import logging
import re
from .base import BaseCrawler
from playwright.sync_api import Page
from typing import List, Dict, Any

class InThisWorkCrawler(BaseCrawler):
    def __init__(self, page: Page):
        super().__init__(page)

    def _extract_id(self, raw: str) -> int:
        """
        문자열에서 숫자 ID를 추출합니다.
        예: 'post-1234' -> 1234
        """
        try:
            match = re.search(r'(\d+)', raw)
            return int(match.group(1)) if match else -1
        except:
            return -1

    def crawl(self, url: str, latest_index: int) -> tuple[List[Dict[str, Any]], int]:
        """
        목록 페이지를 크롤링하여 새로운 공고를 식별하고 기본 정보를 수집합니다.
        
        Args:
            url (str): 대상 목록 페이지 URL
            latest_index (int): 마지막으로 수집했던 공고의 ID (Incremental Crawling 기준점)
            
        Returns:
            tuple: (새로 발견된 공고 리스트, 갱신된 최신 ID)
        """
        logging.info(f"목록 페이지 방문: {url}")
        self.page.goto(url, wait_until="networkidle", timeout=60000)

        # 게시글 목록 래퍼(Wrapper) 요소 확인
        wrapper = self.page.query_selector("[id^='dpt-wrapper']")
        if not wrapper:
            return [], latest_index

        entries = wrapper.query_selector_all("div.dpt-entry[data-id]")
        collected = []
        newest_id = latest_index

        for entry in entries:
            # 1. ID 추출 및 중복 검사 (이미 수집한 공고는 스킵)
            content_id_str = entry.get_attribute("data-id")
            content_id = self._extract_id(content_id_str)
            if content_id <= latest_index:
                continue

            # 2. 신입 필터링 (핵심 비즈니스 로직)
            # data-category 속성과 시각적으로 표시된 카테고리 텍스트 모두 검사
            category_attr = entry.get_attribute("data-category") or ""
            category_text_el = entry.query_selector(".dpt-cat-link") 
            category_vis = category_text_el.text_content() if category_text_el else ""
            
            # '신입' 키워드가 포함되지 않은 경력직 공고 등은 제외
            if "신입" not in category_attr and "신입" not in category_vis:
                logging.info(f"스킵됨 (신입 아님): ID {content_id}")
                continue

            # 3. 기본 메타 데이터 수집
            full_title = entry.get_attribute("data-title") or entry.text_content().strip()
            link_el = entry.query_selector("a")
            detail_url = link_el.get_attribute("href") if link_el else url
            
            # 제목 파싱: "회사명 ｜ 공고제목" 형식 분리 시도
            company = ""
            title = full_title
            if "｜" in full_title:
                parts = full_title.split("｜", 1)
                company = parts[0].strip()
                title = parts[1].strip()
            
            # 분리 실패 시 회사명 임의 지정 (추후 상세 페이지에서 보정 가능)
            if not company: 
                company = "Company" 

            # 최신 ID 갱신 (가장 큰 ID 값 유지)
            newest_id = max(newest_id, content_id)
            
            collected.append({
                "id": content_id,
                "url": detail_url,
                "company": company,
                "title": title,
                "category_raw": category_vis or category_attr
            })

        return collected, newest_id

    def parse_detail(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        상세 페이지에 접속하여 본문 텍스트, 이미지 URL, 실제 지원 링크를 정밀하게 추출합니다.
        """
        url = post['url']
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=40000)
            
            # --- [1] 실제 지원 링크(ATS 등) 추출 ---
            real_apply_link = ""
            # 사이트 특화 선택자: .maxbutton-6 클래스가 주로 지원 버튼에 사용됨
            apply_btn = self.page.query_selector("a.maxbutton-6")
            if not apply_btn:
                 # 클래스 매칭 실패 시 텍스트 기반 폴백(Fallback) 검색
                 apply_btn = self.page.query_selector("a:has-text('지원하러 가기')")
            
            if apply_btn:
                real_apply_link = apply_btn.get_attribute("href")

            # --- [2] 본문 텍스트 추출 전략 ---
            text_content = ""
            
            # 전략 A: 메인 콘텐츠 블록(.fusion-content-tb) 우선 탐색
            # 이 영역이 가장 정확한 채용 정보를 담고 있을 확률이 높음
            content_block = self.page.query_selector(".fusion-content-tb")
            
            if content_block:
                text_content = content_block.text_content().strip()
            else:
                # 전략 B: 메인 블록 부재 시 모든 컬럼 래퍼의 텍스트 수집
                # 너무 짧은 텍스트(메뉴, 헤더 등 노이즈)는 필터링하여 병합
                wrappers = self.page.query_selector_all(".fusion-column-wrapper")
                texts = [w.text_content().strip() for w in wrappers]
                text_content = "\n".join([t for t in texts if len(t) > 30])

            # 불필요한 공백 및 줄바꿈 정규화
            text_content = re.sub(r'\s+', ' ', text_content).strip()

            # --- [3] 이미지 URL 추출 (멀티모달 요약용) ---
            image_url = ""
            # 본문 영역 내 이미지를 우선적으로 탐색
            target_area = content_block if content_block else self.page.query_selector("body")
            
            imgs = target_area.query_selector_all("img")
            for img in imgs:
                src = img.get_attribute("src")
                # 유효한 이미지 확장자 검사 및 Base64(Data URI) 제외
                if src and ("jpg" in src or "png" in src) and not src.startswith("data:"):
                    # 첫 번째 유효 이미지를 대표 이미지로 선정 (필요 시 로직 고도화 가능)
                    image_url = src
                    break

            return {
                **post,
                "real_apply_link": real_apply_link,
                "text_content": text_content,
                "image_url": image_url
            }

        except Exception as e:
            logging.error(f"상세 페이지 파싱 실패 ({url}): {e}")
            # 파싱 실패 시에도 크롤링 전체가 중단되지 않도록 기본 정보 반환
            return post