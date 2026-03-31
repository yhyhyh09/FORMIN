"""
LLM 클라이언트 공통 모듈 (Google Gemini REST API)
gRPC/cryptography 의존성 없이 httpx로 직접 호출
"""
from __future__ import annotations
import httpx
from config.settings import GEMINI_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _post(prompt: str) -> str:
    """Gemini generateContent REST 호출"""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    url = f"{_BASE_URL}/{LLM_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": LLM_TEMPERATURE,
            "maxOutputTokens": LLM_MAX_TOKENS,
        },
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, json=payload, params={"key": GEMINI_API_KEY})
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini 응답 없음: {data}")
    return candidates[0]["content"]["parts"][0]["text"]


def chat(prompt: str, system: str = "") -> str:
    """
    단일 프롬프트 호출.
    system 프롬프트는 첫 번째 메시지 앞에 붙여서 전달.
    """
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    return _post(full_prompt)


def chat_with_history(messages: list[dict], system: str = "") -> str:
    """
    대화 히스토리 기반 호출.
    messages: [{"role": "user"|"assistant", "content": "..."}]
    마지막 메시지에 system 컨텍스트를 앞에 붙여서 전달.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")

    # Gemini contents 형식으로 변환
    contents = []
    for i, m in enumerate(messages):
        role = "model" if m["role"] == "assistant" else "user"
        text = m["content"]
        # 마지막 user 메시지에 system context 추가
        if i == len(messages) - 1 and role == "user" and system:
            text = f"{system}\n\n{text}"
        contents.append({"role": role, "parts": [{"text": text}]})

    url = f"{_BASE_URL}/{LLM_MODEL}:generateContent"
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": LLM_TEMPERATURE,
            "maxOutputTokens": LLM_MAX_TOKENS,
        },
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, json=payload, params={"key": GEMINI_API_KEY})
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini 응답 없음: {data}")
    return candidates[0]["content"]["parts"][0]["text"]
