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

# 설정
DATA_PATH = Path("data/homepage.json")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_config():
    load_dotenv()
    is_dry_run = os.getenv("DRY_RUN")
    if is_dry_run is None:
        return False, ""
    is_dry_run = is_dry_run.strip().lower() in {"1", "true", "yes", "on"}
    webhook_url = os.getenv("AID_DISCORD_WEBHOOK_URL", "")
    return is_dry_run, webhook_url

def read_data():
    if not DATA_PATH.exists():
        # 파일이 없으면 기본 구조 반환
        return {"data": []}
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def run():
    dry_run, webhook_url = load_config()
    if not dry_run and not webhook_url:
        logging.error("Webhook URL missing in production mode.")
        return

    logging.info(f"Starting Crawler... (Dry Run: {dry_run})")
    
    db = read_data()
    # 사이트 목록 가져오기 (없으면 빈 리스트)
    sites = db.get('data', [])
    
    final_posts = []
    
    # 데이터 변경 여부 플래그
    is_data_updated = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # [수정] 사이트 리스트를 직접 순회
        for site in sites:
            url = site.get('url')
            # 각 사이트별로 저장된 마지막 인덱스를 가져옴 (없으면 -1)
            current_latest_index = site.get('latestPostIndex', -1)
            
            logging.info(f"Processing site: {site.get('homepage', 'Unknown')} (Latest Index: {current_latest_index})")

            # 현재는 크롤러가 하나지만, 추후 site['crawler_type'] 등으로 분기 가능
            crawler = InThisWorkCrawler(page)
            
            try:
                # 크롤링 수행 (해당 사이트의 최신 인덱스 기준)
                candidates, new_latest_id = crawler.crawl(url, current_latest_index)
                
                # 유효한 공고 처리
                valid_post_count = 0
                for post in candidates:
                    if dry_run and valid_post_count >= 3:
                        logging.info("🛑 [Dry Run] 3 posts limit reached for this site.")
                        break

                    check_text = f"{post['company']} {post['title']}"
                    
                    if ai.is_ai_job(check_text):
                        logging.info(f"Accepted: {check_text}")
                        
                        # 상세 페이지 파싱
                        detailed_post = crawler.parse_detail(post)
                        content = detailed_post.get('text_content', "")
                        image_url = detailed_post.get('image_url', "")

                        logging.info("Requesting Gemini summarization...")
                        detailed_post['summary'] = ai.summarize_text(
                            text=content,
                            company=detailed_post['company'],
                            title=detailed_post['title'],
                            image_url=image_url
                        )
                        detailed_post['category_label'] = ai.classify_text(check_text)
                        
                        final_posts.append(detailed_post)
                        valid_post_count += 1
                    else:
                        logging.info(f"Skipped (Non-AI): {check_text}")

                # [중요] 실제 전송 모드(Dry Run False)일 때만 인덱스 업데이트
                if not dry_run and new_latest_id > current_latest_index:
                    site['latestPostIndex'] = new_latest_id
                    is_data_updated = True
                    logging.info(f"Updated index for {site.get('homepage')} -> {new_latest_id}")

            except Exception as e:
                logging.error(f"Error crawling {url}: {e}")

        browser.close()

    # 결과 처리
    if final_posts:
        if dry_run:
            logging.info(f"DRY RUN: Found {len(final_posts)} posts.")
            import pprint
            pprint.pprint(final_posts)
        else:
            discord.send_discord_embed(webhook_url, final_posts)
            logging.info("Sent messages to Discord.")
            
            # 변경사항이 있으면 저장
            if is_data_updated:
                save_data(db)
                logging.info("Saved updated homepage.json")
    else:
        logging.info("No new posts found.")

if __name__ == "__main__":
    start = time.time()
    run()
    logging.info(f"Finished in {time.time() - start:.2f}s")