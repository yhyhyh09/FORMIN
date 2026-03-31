"""
컴플라이언스 검사 모듈
한국 공시 규정(자본시장법, 코스피/코스닥 공시 규정) 준수 여부 체크
"""
from __future__ import annotations
import re
from datetime import datetime

# 선별공시 금지 표현 패턴
_SELECTIVE_DISCLOSURE_PATTERNS = [
    r"구체적\s*목표\s*주가",
    r"(\d+)원\s*(목표|예상|전망)",
    r"(EPS|BPS|ROE|ROA)\s*\d+",
    r"다음\s*분기\s*(매출|이익)\s*\d+",
    r"미공개\s*(정보|사실)",
]

# SPAC 관련 사용 주의 표현
_CAUTION_EXPRESSIONS = [
    "보장", "확실", "반드시", "무조건", "위험 없음", "손실 없음",
]

# 필수 포함 문구 (IR 자료 기준)
_REQUIRED_DISCLAIMERS = [
    "forward-looking",
    "미래 예측",
    "투자 판단",
    "리스크",
]


def check_selective_disclosure(narrative: str) -> list[str]:
    """선별공시 위반 가능 표현 탐지"""
    flags = []
    for pattern in _SELECTIVE_DISCLOSURE_PATTERNS:
        if re.search(pattern, narrative, re.IGNORECASE):
            flags.append(f"[선별공시 위험] 패턴 발견: `{pattern}`")
    return flags


def check_caution_expressions(narrative: str) -> list[str]:
    """투자 과대포장 표현 탐지"""
    flags = []
    for expr in _CAUTION_EXPRESSIONS:
        if expr in narrative:
            flags.append(f"[주의 표현] '{expr}' 사용됨 — 수정 권고")
    return flags


def check_required_elements(narrative: str) -> list[str]:
    """필수 면책 문구 누락 탐지"""
    flags = []
    for req in _REQUIRED_DISCLAIMERS:
        if req.lower() not in narrative.lower():
            flags.append(f"[필수 요소 누락] '{req}' 관련 면책 문구 없음")
    return flags


def check_timing_compliance() -> list[str]:
    """
    공시 타이밍 준수 검사
    - 실적 발표 전 IR 자료 배포 금지 (quiet period)
    - 정기주총 전 30일: 중요 사항 공시 주의
    """
    flags = []
    today = datetime.now()
    # 분기말 전후 15일 quiet period 예시
    month = today.month
    day = today.day
    if month in (1, 4, 7, 10) and day <= 15:
        flags.append(
            f"[타이밍 주의] 현재 실적 발표 시즌({today.strftime('%Y-%m-%d')}) — "
            "미확정 실적 언급 금지"
        )
    return flags


def run_full_compliance_check(narrative: str, messages: list[dict] | None = None) -> dict:
    """
    전체 컴플라이언스 검사 실행
    Returns: {passed: bool, flags: [str], timestamp: str}
    """
    flags: list[str] = []
    flags.extend(check_selective_disclosure(narrative))
    flags.extend(check_caution_expressions(narrative))
    flags.extend(check_required_elements(narrative))
    flags.extend(check_timing_compliance())

    # 개인화 메시지도 검사
    if messages:
        for msg in messages:
            text = msg.get("message", "")
            flags.extend(check_selective_disclosure(text))
            flags.extend(check_caution_expressions(text))

    passed = len(flags) == 0
    return {
        "passed": passed,
        "flags": flags,
        "flag_count": len(flags),
        "timestamp": datetime.now().isoformat(),
        "recommendation": (
            "컴플라이언스 검토 완료 — 배포 승인 가능" if passed
            else f"{len(flags)}개 항목 수정 필요"
        ),
    }
