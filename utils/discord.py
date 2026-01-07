import requests
import logging
import time
from typing import List, Dict

def send_discord_embed(webhook_url: str, posts: List[Dict]):
    """
    수집된 채용 공고 리스트를 Discord Webhook을 통해 Embed 메시지로 전송합니다.
    Discord API 제한을 고려하여 배치 단위로 분할 전송합니다.
    """
    if not webhook_url or not posts:
        return

    # Discord 웹훅은 단일 요청당 최대 10개의 Embed만 허용합니다.
    # 안정성을 위해 5개 단위로 청크를 나누어 순차적으로 전송합니다.
    chunk_size = 5
    for i in range(0, len(posts), chunk_size):
        chunk = posts[i:i+chunk_size]
        
        embeds = []
        for post in chunk:
            # 지원 링크(real_apply_link)가 존재하면 우선 사용하고, 없을 경우 원본 URL로 대체
            apply_link = post.get('real_apply_link')
            origin_link = post.get('url')
            
            # 마크다운을 사용하여 클릭 가능한 하이퍼링크 텍스트 구성
            links_text = f"[📄 채용 공고 원문]({origin_link})"
            if apply_link:
                links_text = f"[🚀 **지원하러 가기**]({apply_link}) | " + links_text

            # 개별 공고에 대한 Embed 객체 생성
            embed = {
                "title": f"[{post['company']}] {post['title']}",
                "url": apply_link if apply_link else origin_link, # 제목 클릭 시 이동 경로
                "color": 5814783, # 보라색 계열 (Decimal Color Code)
                # "fields": [
                #     {
                #         "name": "📂 분류",
                #         # 원본 카테고리 데이터와 매핑된 라벨을 함께 표시하여 데이터 검증 용이성 확보
                #         "value": f"`{post['category_label']}` (원본: {post.get('category_raw', 'N/A')})",
                #         "inline": True
                #     }
                # ],
                "description": f"{post['summary']}\n\n{links_text}",
                # "footer": {
                #     "text": "InThisWork AI Crawler"
                #}
            }
            embeds.append(embed)

        # Discord Webhook 페이로드 구성
        payload = {
            "content": "## 📢 오늘의 채용 공고", # 메시지 헤더 (Optional)
            "embeds": embeds
        }

        # 최대 3번 재시도
        for attempt in range(3):
            try:
                # Webhook POST 요청 전송
                resp = requests.post(webhook_url, json=payload)
                if resp.status_code in [200, 204]:
                    break # 성공하면 루프 탈출
                
                # 429(Too Many Requests)나 500번대 에러면 대기 후 재시도
                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    logging.warning(f"Discord 전송 실패 ({resp.status_code}). 5초 후 재시도...")
                    time.sleep(5)
                else:
                    logging.error(f"Discord 전송 실패 (Status: {resp.status_code}): {resp.text}")
                    break
            except Exception as e:
                logging.error(f"Discord 요청 중 예외 발생: {e}")
                time.sleep(5)
