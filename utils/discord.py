import requests
import logging
from typing import List, Dict

def send_discord_embed(webhook_url: str, posts: List[Dict]):
    """
    Discord Webhook으로 Embed 메시지를 전송합니다.
    """
    if not webhook_url or not posts:
        return

    # Embed는 한 번에 최대 10개까지만 전송 가능하므로 청크로 나눔 (안전하게 5개씩)
    chunk_size = 5
    for i in range(0, len(posts), chunk_size):
        chunk = posts[i:i+chunk_size]
        
        embeds = []
        for post in chunk:
            # 실제 지원 링크가 있으면 그것을, 없으면 소개 페이지(url)를 사용
            apply_link = post.get('real_apply_link')
            origin_link = post.get('url')
            
            # 링크 텍스트 구성
            links_text = f"[📄 채용 공고 원문]({origin_link})"
            if apply_link:
                links_text = f"[🚀 **지원하러 가기**]({apply_link}) | " + links_text

            embed = {
                "title": f"[{post['company']}] {post['title']}",
                "url": apply_link if apply_link else origin_link, # 제목 클릭 시 이동할 곳
                "color": 5814783, # 예쁜 파란색/보라색 계열
                "fields": [
                    {
                        "name": "📂 분류",
                        "value": f"`{post['category_label']}` (원본: {post.get('category_raw', 'N/A')})",
                        "inline": True
                    }
                ],
                "description": f"**📌 요약**\n{post['summary']}\n\n{links_text}",
                "footer": {
                    "text": "InThisWork AI Crawler"
                }
            }
            embeds.append(embed)

        payload = {
            "content": "## 📢 오늘의 신입 AI/Data 채용 공고", # 메시지 상단 멘트
            "embeds": embeds
        }

        try:
            resp = requests.post(webhook_url, json=payload)
            if resp.status_code not in [200, 204]:
                logging.error(f"Failed to send Discord: {resp.text}")
        except Exception as e:
            logging.error(f"Discord send error: {e}")