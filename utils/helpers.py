"""
공통 유틸리티 함수
"""
from __future__ import annotations
import re
from datetime import datetime


def clean_text(text: str) -> str:
    """불필요한 공백, 특수문자 정제"""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def truncate(text: str, max_len: int = 200, suffix: str = "...") -> str:
    """텍스트 길이 제한"""
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix


def format_date(date_str: str) -> str:
    """DART 날짜 형식(YYYYMMDD) → 표시용 형식(YYYY-MM-DD)"""
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def format_number(value: float | int, unit: str = "") -> str:
    """숫자 포맷: 1,234,567원 형식"""
    try:
        formatted = f"{int(value):,}"
        return f"{formatted}{unit}" if unit else formatted
    except (ValueError, TypeError):
        return str(value)


def sentiment_to_emoji(label: str) -> str:
    """sentiment 레이블 → 이모지"""
    mapping = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}
    return mapping.get(label, "⚪")


def now_str() -> str:
    """현재 시각 문자열"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def extract_json_from_text(text: str) -> dict | list | None:
    """LLM 응답에서 JSON 블록 추출"""
    import json
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*([\[{].*?[\]}])\s*```',
        r'(\{.*\})',
        r'(\[.*\])',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None
