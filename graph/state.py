"""
LangGraph 공유 상태 정의
IRState는 모든 에이전트 노드가 읽고 쓰는 단일 상태 객체다.
"""
from __future__ import annotations
from typing import Annotated, Any
from typing_extensions import TypedDict
import operator


def _append(existing: list, new: list | Any) -> list:
    """리스트 필드 병합 reducer: 새 항목을 기존 목록에 추가"""
    if isinstance(new, list):
        return existing + new
    return existing + [new]


class IRState(TypedDict):
    # ── 입력 ──────────────────────────────────────────────
    company_code: str                       # DART 종목 코드 (e.g. "005930")
    company_name: str                       # 기업명

    # ── 모니터링 & 인텔리전스 ──────────────────────────────
    dart_filings: Annotated[list[dict], _append]       # 수집된 공시 목록
    news_items: Annotated[list[dict], _append]         # 뉴스/sentiment 항목
    market_signals: Annotated[list[dict], _append]     # 주가·거래량 신호
    strategy_gaps: list[str]                           # 탐지된 Gap 목록

    # ── 나레이티브 ────────────────────────────────────────
    narrative_draft: str                    # 생성된 IR 나레이티브 (Markdown)
    qa_pairs: list[dict]                    # 예상 Q&A 목록 [{q, a}, ...]
    briefing_pack: dict                     # 브리핑팩 메타데이터

    # ── 투자자 프로파일 & 타깃팅 ──────────────────────────
    investor_profiles: list[dict]           # 전체 투자자 프로파일
    targeted_investors: list[dict]          # 타깃팅된 투자자 (score 포함)
    personalized_messages: list[dict]       # 투자자별 맞춤 메시지

    # ── 컴플라이언스 ──────────────────────────────────────
    compliance_flags: list[str]             # 위반 또는 주의 항목
    compliance_passed: bool                 # 최종 통과 여부

    # ── 감사 로그 ─────────────────────────────────────────
    audit_trail: Annotated[list[dict], _append]  # 에이전트 액션 기록

    # ── Human-in-the-loop ─────────────────────────────────
    human_approval: str | None              # "approved" | "rejected" | None
    rejection_reason: str | None            # 반려 사유

    # ── 제어 ──────────────────────────────────────────────
    current_step: str                       # 현재 실행 중인 단계
    error: str | None                       # 오류 메시지
    iteration_count: int                    # 나레이티브 재생성 횟수
    messages: Annotated[list[dict], _append]  # 에이전트 간 메시지 로그


def initial_state(company_code: str, company_name: str) -> IRState:
    """초기 상태 생성 헬퍼"""
    return IRState(
        company_code=company_code,
        company_name=company_name,
        dart_filings=[],
        news_items=[],
        market_signals=[],
        strategy_gaps=[],
        narrative_draft="",
        qa_pairs=[],
        briefing_pack={},
        investor_profiles=[],
        targeted_investors=[],
        personalized_messages=[],
        compliance_flags=[],
        compliance_passed=False,
        audit_trail=[],
        human_approval=None,
        rejection_reason=None,
        current_step="start",
        error=None,
        iteration_count=0,
        messages=[],
    )
