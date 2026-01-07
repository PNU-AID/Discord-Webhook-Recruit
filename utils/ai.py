import os
import logging
import requests
from transformers import pipeline
from dotenv import load_dotenv  # 환경변수 로드용
from PIL import Image
from io import BytesIO

# [핵심] 구글의 최신 라이브러리 (google-genai) 임포트
# 기존 google.generativeai는 사용하지 않습니다.
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# 1. 환경 변수 강제 로드 (가장 먼저 실행)
load_dotenv()

# 2. 분류 모델 설정 (유지)
CLASSIFIER_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
LABELS = ["AI/인공지능", "데이터/분석", "연구", "웹/앱 개발", "기타"]
POSITIVE_LABELS = {"AI/인공지능", "데이터/분석", "연구"}

_classifier = None
_client = None  # Gemini Client

def get_classifier():
    global _classifier
    if not _classifier:
        _classifier = pipeline("zero-shot-classification", model=CLASSIFIER_MODEL, device=-1)
    return _classifier

def get_gemini_client():
    global _client
    if not _client:
        # .env에서 키를 가져옵니다.
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.error("❌ GEMINI_API_KEY is missing in .env file!")
            return None
        
        if not genai:
            logging.error("❌ google-genai library is not installed! Run: pip install google-genai")
            return None

        # 신규 SDK 클라이언트 초기화 (v1alpha/v1beta 자동 처리)
        try:
            _client = genai.Client(api_key=api_key)
        except Exception as e:
            logging.error(f"Failed to initialize Gemini Client: {e}")
            return None
    return _client

def classify_text(text: str) -> str:
    if len(text) < 2: return "기타"
    try:
        classifier = get_classifier()
        result = classifier(text, LABELS, hypothesis_template="This job is about {}.")
        return result["labels"][0]
    except Exception as e:
        logging.warning(f"Classification failed: {e}")
        return "기타"

def is_ai_job(text: str) -> bool:
    return classify_text(text) in POSITIVE_LABELS

def download_image(image_url: str):
    """
    URL에서 이미지를 다운로드하여 PIL Image 객체로 변환
    """
    try:
        if not image_url: return None
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        logging.warning(f"Failed to download image: {e}")
        return None

def summarize_text(text: str, company: str = "", title: str = "", image_url: str = "") -> str:
    """
    Gemini 2.5 Flash (New SDK)를 사용하여 채용 공고를 분석합니다.
    """
    client = get_gemini_client()
    if not client:
        return "⚠️ API 키 설정 오류 또는 라이브러리 미설치"

    try:
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
        
        contents = [prompt_text]

        # 이미지 처리 (이미지가 있으면 리스트에 추가)
        if image_url:
            image_obj = download_image(image_url)
            if image_obj:
                logging.info("Run Gemini with Image...")
                contents.append(image_obj)
            else:
                logging.info("Image download failed, running with text only.")

        # 생성 요청 (신규 SDK 문법)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents
        )
        
        return response.text.strip()

    except Exception as e:
        # 에러 발생 시 로그를 명확히 출력
        logging.error(f"Gemini Summarization failed: {e}")
        return "요약 생성 중 오류가 발생했습니다."

# 구버전 호환성을 위해 남겨둔 빈 함수들 (main.py 에러 방지용)
def run_ocr(image_url: str) -> str: return ""