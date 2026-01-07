# main.py
import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from crawlers.inthiswork import InThisWorkCrawler
from utils import ai, discord

# --- 설정 및 상수 정의 ---
DATA_PATH = Path("data/homepage.json")

# 로깅 설정: 타임스탬프와 로그 레벨을 포함하여 디버깅 용이성 확보
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_config():
    """
    환경 변수(.env)를 로드하고 실행 모드(Dry Run)와 Webhook URL을 반환합니다.
    """
    load_dotenv()
    
    # Dry Run 모드 확인 (대소문자 구분 없이 다양한 True 표기 지원)
    is_dry_run_env = os.getenv("DRY_RUN")
    if is_dry_run_env is None:
        is_dry_run = False
    else:
        is_dry_run = is_dry_run_env.strip().lower() in {"1", "true", "yes", "on"}
        
    webhook_url = os.getenv("AID_DISCORD_WEBHOOK_URL", "")
    return is_dry_run, webhook_url

def read_data():
    """
    데이터 파일(homepage.json)을 읽어옵니다. 파일이 없으면 기본 구조를 반환합니다.
    """
    if not DATA_PATH.exists():
        return {"data": []}
    
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    """
    변경된 데이터를 JSON 파일로 저장합니다. (UTF-8 인코딩, 들여쓰기 적용)
    """
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def run():
    """
    메인 크롤링 파이프라인을 실행합니다.
    Flow: 설정 로드 -> 데이터 로드 -> 브라우저 실행 -> 사이트별 크롤링 -> 필터링/요약 -> 결과 전송 -> 상태 저장
    """
    dry_run, webhook_url = load_config()

    # 프로덕션 모드인데 Webhook URL이 없으면 실행 중단
    if not dry_run and not webhook_url:
        logging.error("설정 오류: 프로덕션 모드에서는 Webhook URL이 필수입니다.")
        return

    logging.info(f"크롤러 시작... (모드: {'Dry Run (시뮬레이션)' if dry_run else 'Production (실전송)'})")
    
    db = read_data()
    sites = db.get('data', [])
    
    final_posts = []
    is_data_updated = False # 데이터 변경(인덱스 업데이트) 여부 플래그

    # Playwright 컨텍스트 매니저 사용 (리소스 자동 해제)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 단일 페이지 인스턴스를 재사용하여 리소스 절약
        page = browser.new_page()
        
        # 등록된 각 채용 사이트 순회
        for site in sites:
            url = site.get('url')
            # 증분 크롤링(Incremental Crawling)을 위해 마지막으로 수집한 게시글 인덱스 로드
            current_latest_index = site.get('latestPostIndex', -1)
            
            logging.info(f"사이트 처리 중: {site.get('homepage', 'Unknown')} (Last Index: {current_latest_index})")

            # Crawler 인스턴스 생성 (필요 시 factory 패턴으로 확장 가능)
            crawler = InThisWorkCrawler(page)
            
            try:
                # 1. 크롤링 수행 (새로운 게시글 후보군 추출)
                candidates, new_latest_id = crawler.crawl(url, current_latest_index)
                
                valid_post_count = 0
                for post in candidates:
                    # [Dry Run] API 쿼터 보호를 위해 사이트당 최대 3개까지만 처리
                    if dry_run and valid_post_count >= 3:
                        logging.info("[Dry Run] 테스트 제한 도달 (3개), 해당 사이트 스킵.")
                        break

                    check_text = f"{post['company']} {post['title']}"
                    
                    # 2. 1차 필터링: AI 관련 직무인지 판별 (Zero-shot classification)
                    if ai.is_ai_job(check_text):
                        logging.info(f"AI 공고 감지됨: {check_text}")
                        
                        # 3. 상세 페이지 파싱 (본문, 이미지 등)
                        detailed_post = crawler.parse_detail(post)
                        content = detailed_post.get('text_content', "")
                        image_url = detailed_post.get('image_url', "")

                        # 4. 2차 가공: Gemini를 이용한 요약 및 구조화
                        logging.info("Gemini 요약 요청 중...")
                        detailed_post['summary'] = ai.summarize_text(
                            text=content,
                            company=detailed_post['company'],
                            title=detailed_post['title'],
                            image_url=image_url
                        )
                        # 분류 라벨링 추가
                        detailed_post['category_label'] = ai.classify_text(check_text)
                        
                        final_posts.append(detailed_post)
                        valid_post_count += 1
                    else:
                        logging.info(f"PASS (비관련 직무): {check_text}")

                # [State Management] 프로덕션 모드일 때만 최신 게시글 인덱스(Cursor)를 업데이트
                # Dry Run 중에 인덱스를 업데이트하면 실제 실행 시 데이터를 놓칠 수 있음
                if not dry_run and new_latest_id > current_latest_index:
                    site['latestPostIndex'] = new_latest_id
                    is_data_updated = True
                    logging.info(f"인덱스 업데이트 예약: {site.get('homepage')} -> {new_latest_id}")

            except Exception as e:
                logging.error(f"크롤링 중 예외 발생 ({url}): {e}")

        browser.close()

    # --- 결과 처리 및 전송 ---
    if final_posts:
        if dry_run:
            logging.info(f"[Dry Run] 총 {len(final_posts)}개의 공고가 수집되었습니다. (전송 건너뜀)")
            import pprint
            pprint.pprint(final_posts)
        else:
            # Discord 전송
            discord.send_discord_embed(webhook_url, final_posts)
            logging.info("Discord 알림 전송 완료.")
            
            # 변경된 상태(인덱스) 저장
            if is_data_updated:
                save_data(db)
                logging.info("homepage.json 업데이트 완료.")
    else:
        logging.info("새로운 채용 공고가 없습니다.")

if __name__ == "__main__":
    start = time.time()
    try:
        run()
    except KeyboardInterrupt:
        logging.info("사용자에 의해 중단됨.")
    except Exception as e:
        logging.error(f"치명적인 오류 발생: {e}", exc_info=True)
    finally:
        logging.info(f"실행 시간: {time.time() - start:.2f}초")