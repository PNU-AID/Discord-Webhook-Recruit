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

# 지연 로딩(Lazy Loading)을 위한 싱글톤 인스턴스
_classifier = None
_client = None

def get_classifier():
    """
    제로샷(Zero-Shot) 분류 파이프라인을 초기화하고 반환합니다.
    모듈 임포트 시 불필요한 오버헤드를 줄이기 위해 지연 로딩을 사용합니다.
    """
    global _classifier
    if not _classifier:
        # device=-1은 CPU 실행을 강제합니다. (CUDA 사용 시 0으로 변경)
        _classifier = pipeline("zero-shot-classification", model=CLASSIFIER_MODEL, device=-1)
    return _classifier

def get_gemini_client():
    """
    API 키 유효성 검사와 함께 구글 GenAI 클라이언트를 초기화합니다.
    라이브러리가 없거나 키가 유효하지 않으면 None을 반환합니다.
    """
    global _client
    if not _client:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.error("환경 변수에 GEMINI_API_KEY가 없습니다.")
            return None
        
        if not genai:
            logging.error("google-genai 라이브러리를 찾을 수 없습니다. 'pip install google-genai'를 실행하세요.")
            return None

        try:
            _client = genai.Client(api_key=api_key)
        except Exception as e:
            logging.error(f"GenAI 클라이언트 초기화 실패: {e}")
            return None
    return _client

def classify_text(text: str) -> str:
    """
    제로샷 분류(Zero-Shot Classification)를 사용하여 직무 설명을 사전 정의된 카테고리로 분류합니다.
    분류 실패나 텍스트가 너무 짧을 경우 '기타'를 반환합니다.
    """
    if len(text) < 2:
        return "기타"
    
    try:
        classifier = get_classifier()
        # 가설(Hypothesis) 템플릿을 사용하여 NLI 모델의 정확도 향상
        result = classifier(text, LABELS, hypothesis_template="This job is about {}.")
        return result["labels"][0]
    except Exception as e:
        logging.warning(f"분류 추론(Inference) 실패: {e}")
        return "기타"

def is_ai_job(text: str) -> bool:
    """채용 공고가 AI/데이터/연구와 관련이 있는지 판별합니다."""
    return classify_text(text) in POSITIVE_LABELS

def download_image(image_url: str) -> Optional[Image.Image]:
    """
    URL에서 이미지를 다운로드하여 PIL Image 객체로 변환합니다.
    실패 시 None을 반환합니다.
    """
    try:
        if not image_url:
            return None
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        logging.warning(f"이미지 다운로드 실패: {e}")
        return None

def summarize_text(text: str, company: str = "", title: str = "", image_url: str = "") -> str:
    """
    Gemini 2.5 Flash를 사용하여 구조화된 직무 요약을 생성합니다.
    이미지 URL이 제공되면 멀티모달 입력(텍스트+이미지)을 지원하며, 503 오류 발생 시 재시도합니다.
    """
    client = get_gemini_client()
    if not client:
        return "설정 오류: API 키 또는 라이브러리 설치를 확인하세요."

    # 프롬프트 구성
    prompt_text = f"""
You are an expert IT Tech Recruiter.
Analyze the provided job posting content (and image if available) to extract key information.
Respond strictly in Korean.

**Company**: {company}
**Job Title**: {title}

**Output Format:**
🎯 **핵심 요약**: (One sentence summary)
🔑 **주요 업무**: (Bullet points)
✅ **자격 요건**: (Bullet points, hard skills focus)
🛠 **기술 스택**: (Tools, Languages, Frameworks. If none, write '정보 없음')

---
[Text Content]
{text[:15000]}
"""
    # 멀티모달 생성을 위한 페이로드 구성
    contents = [prompt_text]

    if image_url:
        image_obj = download_image(image_url)
        if image_obj:
            logging.info("멀티모달 콘텐츠 처리 중 (텍스트 + 이미지)")
            contents.append(image_obj)
        else:
            logging.info("이미지 다운로드 실패, 텍스트로만 진행합니다.")

    # --- 재시도(Retry) 로직 ---
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 신규 SDK 인터페이스를 사용하여 콘텐츠 생성
            response = client.models.generate_content(
                model=GEMINI_MODEL_ID,
                contents=contents
            )
            
            # Gemini Free Tier는 분당 요청 제한이 있으므로 필수입니다.
            time.sleep(4)
            
            return response.text.strip()

        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                # 429 에러(제한 초과)가 뜨면 60초 푹 쉬었다가 재시도
                logging.warning("API 제한 초과 (429). 60초 후 재시도...")
                time.sleep(60)
            elif "503" in str(e) or "Overloaded" in str(e) or "UNAVAILABLE" in str(e):
                # 503(Overloaded) 등 일시적 서버 오류일 경우 대기 후 재시도
                wait_time = 2 * (attempt + 1)
                logging.warning(f"Gemini 서버 혼잡 (503). {wait_time}초 후 재시도... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                logging.error(f"Gemini 생성 실패: {e}")
                return "요약 생성 중 오류가 발생했습니다."
    
    return "서버 혼잡으로 인해 요약을 생성하지 못했습니다."

# --- 레거시 호환성 / 스텁(Stubs) ---
def run_ocr(image_url: str) -> str:
    """Deprecated: 레거시 코드의 임포트 에러 방지를 위한 Placeholder입니다."""
    return ""