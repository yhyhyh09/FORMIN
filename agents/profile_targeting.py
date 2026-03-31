"""
Profile & Targeting Agent
투자자 프로파일링, 타깃팅 스코어링, 13F 스타일 보유 분석
"""
from __future__ import annotations
from graph.state import IRState
from tools.dart_api import search_corp_code, get_large_shareholder_changes, get_major_holder_report
from tools.investor_data import (
    build_investor_profiles,
    target_top_investors,
    get_sample_investors,
)
from utils.audit import record_action


def profile_targeting_agent(state: IRState) -> IRState:
    """
    3단계: 투자자 프로파일 구축 및 타깃 투자자 선정
    """
    company_name = state["company_name"]
    narrative_draft = state.get("narrative_draft", "")

    record_action(state, "profile_targeting_agent", "start", {"company": company_name})

    # ── 나레이티브 핵심 테마 추출 ─────────────────────────
    narrative_themes = _extract_themes(narrative_draft)

    # ── DART 대량보유 공시 기반 투자자 데이터 ─────────────
    raw_holder_data: list[dict] = []
    try:
        corp_code = search_corp_code(company_name)
        if corp_code:
            large_holders = get_large_shareholder_changes(corp_code, days=180)
            major_holders = get_major_holder_report(corp_code)
            raw_holder_data = large_holders + major_holders
    except Exception as e:
        record_action(state, "profile_targeting_agent", "dart_fallback", {"error": str(e)})

    # API 실패 또는 데이터 없을 때 샘플 사용
    if not raw_holder_data:
        raw_holder_data = get_sample_investors()

    # ── 투자자 프로파일 구축 ──────────────────────────────
    company_profile = {
        "sector": _infer_sector(company_name),
        "market_cap": "large",
        "dividend_yield": 2.5,
        "growth_rate": 8.0,
        "esg_score": 65,
    }

    investor_profiles = build_investor_profiles(raw_holder_data)

    # ── 타깃 투자자 선정 ──────────────────────────────────
    targeted_investors = target_top_investors(
        investor_profiles,
        company_profile,
        narrative_themes,
    )

    record_action(state, "profile_targeting_agent", "complete", {
        "total_profiles": len(investor_profiles),
        "targeted_count": len(targeted_investors),
        "themes": narrative_themes[:5],
    })

    return {
        **state,
        "investor_profiles": investor_profiles,
        "targeted_investors": targeted_investors,
        "current_step": "targeting_complete",
    }


def _extract_themes(narrative: str) -> list[str]:
    """나레이티브에서 핵심 테마 키워드 추출"""
    theme_keywords = [
        "배당", "성장", "수익성", "ESG", "거버넌스", "글로벌", "밸류에이션",
        "시가총액", "유동성", "경쟁우위", "가이던스", "주주환원", "자사주",
        "신성장", "R&D", "M&A", "신규 사업", "원가 절감", "디지털 전환",
        "장기", "단기 촉매", "모멘텀", "리스크", "지정학",
    ]
    found = [kw for kw in theme_keywords if kw in narrative]
    return found if found else ["성장", "수익성", "주주환원"]


def _infer_sector(company_name: str) -> str:
    """기업명 기반 섹터 추론"""
    sector_map = {
        "삼성": "technology",
        "SK": "energy_technology",
        "현대": "automotive",
        "LG": "electronics",
        "롯데": "consumer",
        "포스코": "steel",
        "카카오": "internet",
        "네이버": "internet",
        "셀트리온": "biotech",
        "한국전력": "utilities",
    }
    for keyword, sector in sector_map.items():
        if keyword in company_name:
            return sector
    return "diversified"
