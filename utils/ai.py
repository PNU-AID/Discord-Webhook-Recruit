import os
import logging
import requests
import time
from io import BytesIO
from typing import Optional, Union

from dotenv import load_dotenv
from PIL import Image
from transformers import pipeline

# 구글 GenAI SDK (google-genai)
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# 환경 변수 로드
load_dotenv()

# --- 설정 (Configuration) ---
CLASSIFIER_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
LABELS = ["AI/인공지능", "데이터/분석", "연구", "웹/앱 개발", "기타"]
POSITIVE_LABELS = {"AI/인공지능", "데이터/분석", "연구"}
GEMINI_MODEL_ID = "gemini-2.5-flash"

# 싱글톤 인스턴스
_classifier = None
_client = None

def get_classifier():
    """제로샷 분류 파이프라인 초기화 (Lazy Loading)"""
    global _classifier
    if not _classifier:
        _classifier = pipeline("zero-shot-classification", model=CLASSIFIER_MODEL, device=-1)
    return _classifier

def get_gemini_client():
    """GenAI 클라이언트 초기화"""
    global _client
    if not _client:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.error("환경 변수에 GEMINI_API_KEY가 없습니다.")
            return None
        
        if not genai:
            logging.error("google-genai 라이브러리 미설치.")
            return None

        try:
            _client = genai.Client(api_key=api_key)
        except Exception as e:
            logging.error(f"GenAI 클라이언트 초기화 실패: {e}")
            return None
    return _client

def classify_text(text: str) -> str:
    """직무 설명 텍스트 분류"""
    if len(text) < 2: return "기타"
    try:
        classifier = get_classifier()
        result = classifier(text, LABELS, hypothesis_template="This job is about {}.")
        return result["labels"][0]
    except Exception as e:
        logging.warning(f"분류 실패: {e}")
        return "기타"

def is_ai_job(text: str) -> bool:
    """AI/데이터 관련 직무 판별"""
    return classify_text(text) in POSITIVE_LABELS

def download_image(image_url: str) -> Optional[Image.Image]:
    """이미지 다운로드"""
    try:
        if not image_url: return None
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        logging.warning(f"이미지 다운로드 실패: {e}")
        return None

def summarize_text(text: str, company: str = "", title: str = "", image_url: str = "") -> str:
    """
    Gemini를 사용하여 직무를 요약합니다. (Light Version)
    상세 항목을 제거하고 핵심 요약 위주로 작성하며, IT 직무 추출 강도를 높였습니다.
    """
    client = get_gemini_client()
    if not client:
        return "설정 오류: API 키 확인 필요"

    # [수정된 프롬프트]
    # 1. 상세 항목(주요업무, 자격요건 등) 제거 요청 반영
    # 2. '커넥트웨이브' 사례처럼 총무+전산이 섞인 경우에도 IT 업무를 찾아내도록 지시
    prompt_text = f"""
당신은 IT 테크 리크루터입니다. 채용 공고를 분석하여 핵심 내용을 한국어로 요약하세요.

**Company**: {company}
**Job Title**: {title}

**[분석 지침 - 중요]**
1. **IT 직무 발굴 강화**:
   - 순수 개발직뿐만 아니라 **'전산 운영, IT 인프라, 사내 시스템 관리, 기술 지원'** 등의 업무가 포함되어 있다면 해당 내용을 중심으로 요약하세요.
   - 예: "총무 및 IT 전산" 직무라면, 총무 업무는 제외하고 **IT 전산/인프라 관리 업무만 뽑아서** 요약하세요. "관련 내용 없음"이라고 답하지 마세요.
2. **다중 직무 처리**:
   - 하나의 공고에 여러 IT 직무(예: 백엔드, 프론트엔드)가 있다면 직무별로 나누어 작성하세요.
   - 비-IT 직무(영업, 단순 사무 등)는 철저히 제외하세요.

**[출력 포맷]**
복잡한 항목(자격요건, 기술스택 등)은 모두 제거하고, 아래 형식으로만 답변하세요.

### 📋 [직무명]
> (해당 직무가 하는 IT 업무를 한 문장으로 명확하게 요약)

---
[Text Content]
{text[:15000]}
"""
    contents = [prompt_text]

    if image_url:
        image_obj = download_image(image_url)
        if image_obj:
            logging.info("멀티모달 콘텐츠 처리 중")
            contents.append(image_obj)

    # 재시도 및 API 제한 관리 로직
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL_ID,
                contents=contents
            )
            
            # API 제한(RPM 5) 준수를 위해 20초 대기
            logging.info("API 호출 성공. 20초 대기...")
            time.sleep(20)
            
            raw_text = response.text.strip()
            
            # [앵커 클리닝 로직]
            anchor = "### 📋"
            if anchor in raw_text:
                # 앵커가 발견되면 그 위치부터 끝까지만 사용 (서론 제거)
                start_index = raw_text.find(anchor)
                cleaned_text = raw_text[start_index:]
                return cleaned_text
            else:
                # 앵커가 없으면(모델이 지시를 어기거나 IT 직무가 없는 경우) 원본 반환
                return raw_text
            
        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                logging.warning("API 제한 초과 (429). 60초 대기...")
                time.sleep(60)
            elif "503" in str(e) or "Overloaded" in str(e):
                time.sleep(5)
            else:
                logging.error(f"Gemini 오류: {e}")
                return "요약 생성 실패"
    
    return "서버 혼잡으로 요약 실패"

# --- 레거시 호환성 / 스텁(Stubs) ---
def run_ocr(image_url: str) -> str:
    return ""