import logging
import re
from .base import BaseCrawler
from playwright.sync_api import Page
from typing import List, Dict, Any

class InThisWorkCrawler(BaseCrawler):
    def __init__(self, page: Page):
        super().__init__(page)

    def _extract_id(self, raw: str) -> int:
        try:
            match = re.search(r'(\d+)', raw)
            return int(match.group(1)) if match else -1
        except:
            return -1

    def crawl(self, url: str, latest_index: int) -> tuple[List[Dict[str, Any]], int]:
        logging.info(f"Visiting list page: {url}")
        self.page.goto(url, wait_until="networkidle", timeout=60000)

        # 목록의 첫 번째 wrapper 찾기
        wrapper = self.page.query_selector("[id^='dpt-wrapper']")
        if not wrapper:
            return [], latest_index

        entries = wrapper.query_selector_all("div.dpt-entry[data-id]")
        collected = []
        newest_id = latest_index

        for entry in entries:
            # 1. ID 추출 및 중복 검사
            content_id_str = entry.get_attribute("data-id")
            content_id = self._extract_id(content_id_str)
            if content_id <= latest_index:
                continue

            # 2. 신입 필터링 (가장 중요)
            category_attr = entry.get_attribute("data-category") or ""
            category_text_el = entry.query_selector(".dpt-cat-link") 
            category_vis = category_text_el.text_content() if category_text_el else ""
            
            # "신입" 키워드가 없으면 가차없이 스킵
            if "신입" not in category_attr and "신입" not in category_vis:
                logging.info(f"Skipped (Not Newcomer): ID {content_id}")
                continue

            # 3. 기본 정보 수집
            full_title = entry.get_attribute("data-title") or entry.text_content().strip()
            link_el = entry.query_selector("a")
            detail_url = link_el.get_attribute("href") if link_el else url
            
            # 제목 분리
            company = ""
            title = full_title
            if "｜" in full_title:
                parts = full_title.split("｜", 1)
                company = parts[0].strip()
                title = parts[1].strip()
            # 분리가 안 되었다면 제목을 그대로 쓰고 회사는 공란 혹은 추론
            if not company: 
                company = "Company" 

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
        """ 상세 페이지 로직: 본문(이미지/텍스트) 정밀 추출 + 실제 지원 링크 """
        url = post['url']
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=40000)
            
            # --- [1] 실제 지원 링크 추출 ---
            real_apply_link = ""
            # 이미지에서 확인된 maxbutton-6 클래스 우선 검색
            apply_btn = self.page.query_selector("a.maxbutton-6")
            if not apply_btn:
                 # 없으면 텍스트로 검색
                 apply_btn = self.page.query_selector("a:has-text('지원하러 가기')")
            
            if apply_btn:
                real_apply_link = apply_btn.get_attribute("href")

            # --- [2] 본문 텍스트 추출 전략 고도화 ---
            text_content = ""
            
            # 전략 A: 이미지에 있던 .fusion-content-tb (텍스트 블록) 찾기
            # 이 클래스가 본문 텍스트를 담고 있을 확률이 가장 높음
            content_block = self.page.query_selector(".fusion-content-tb")
            
            if content_block:
                text_content = content_block.text_content().strip()
            else:
                # 전략 B: Text Block이 없으면 모든 fusion-column-wrapper의 텍스트를 긁어모음
                # (첫 번째 wrapper는 제목일 수 있으므로 길이가 긴 것을 선호하거나 다 합침)
                wrappers = self.page.query_selector_all(".fusion-column-wrapper")
                texts = [w.text_content().strip() for w in wrappers]
                # 너무 짧은 텍스트(메뉴, 제목 등)는 제외하고 합침
                text_content = "\n".join([t for t in texts if len(t) > 30])

            # 공백 정리
            text_content = re.sub(r'\s+', ' ', text_content).strip()

            # --- [3] 이미지 URL 추출 (OCR용) ---
            image_url = ""
            # 본문 영역 안의 이미지 우선
            target_area = content_block if content_block else self.page.query_selector("body")
            
            # 크기가 좀 큰 이미지를 찾기 위해 loop (로고 등 제외)
            imgs = target_area.query_selector_all("img")
            for img in imgs:
                src = img.get_attribute("src")
                # jpg, png 이면서 데이터 URI가 아닌 것
                if src and ("jpg" in src or "png" in src) and not src.startswith("data:"):
                    # 보통 본문 이미지는 class에 'wp-image' 등이 붙거나 크기가 큼. 
                    # 여기서는 첫 번째 유효 이미지를 가져오되, 추후 로직 보강 가능
                    image_url = src
                    break

            return {
                **post,
                "real_apply_link": real_apply_link,
                "text_content": text_content,
                "image_url": image_url
            }

        except Exception as e:
            logging.error(f"Error parsing detail {url}: {e}")
            # 에러 나도 기본 정보는 리턴
            return post