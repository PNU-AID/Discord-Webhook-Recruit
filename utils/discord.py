import requests
import logging
import time
from typing import List, Dict

def send_discord_embed(webhook_url: str, posts: List[Dict]):
    """
    채용 공고를 Discord Webhook으로 전송합니다.
    Discord의 2000자 제한을 준수하여 여러 공고를 묶어 전송하며,
    공고 내용이 중간에 잘리지 않도록 처리합니다.
    """
    if not webhook_url or not posts:
        return

    # 메시지 버퍼링 및 전송 로직
    MAX_LENGTH = 1950  # Discord 제한(2000자)보다 약간 여유 있게 설정
    current_message = "# 📢 오늘의 신입 채용 공고\n\n"
    
    for i, post in enumerate(posts):
        origin_link = post.get('url')
        
        # 타이틀 구성 (회사명 - 제목)
        title_line = f"## 🏢 {post['company']}\n## 🧑‍💻 {post['title']}"
        
        # 링크 구성 (인디스워크 원문 링크만 유지, Embed 방지용 <>)
        links = f"[📄 채용 공고 보러가기](<{origin_link}>)"

        # 개별 공고 블록 생성
        post_block = (
            f"{title_line}\n\n"
            f"{post['summary']}\n\n"
            f"{links}\n"
        )
        
        # 길이 체크: 현재 메시지에 새 공고를 더했을 때 제한을 넘는지 확인
        if len(current_message) + len(post_block) > MAX_LENGTH:
            # 제한을 넘으면 지금까지 모은 메시지 전송
            _send_message(webhook_url, current_message)
            
            # 전송 후 현재 공고로 새 메시지 시작
            current_message = post_block
        else:
            # 제한을 넘지 않으면 계속 이어 붙임
            current_message += post_block

    # 루프 종료 후 남은 메시지가 있으면 전송
    if current_message:
        _send_message(webhook_url, current_message)

def _send_message(webhook_url: str, content: str):
    """내부 함수: 실제 메시지 전송 및 재시도 로직"""
    payload = {"content": content}
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(webhook_url, json=payload)
            
            if 200 <= resp.status_code < 300:
                break 
            
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                wait_time = 5 * (attempt + 1)
                logging.warning(f"Discord 전송 지연 ({resp.status_code}). {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                logging.error(f"Discord 전송 실패 (Status: {resp.status_code}): {resp.text}")
                break
        except Exception as e:
            logging.error(f"Discord 요청 중 예외 발생: {e}")
            time.sleep(3)
    
    # 메시지 간 전송 간격 (Rate Limit 보호)
    time.sleep(1)