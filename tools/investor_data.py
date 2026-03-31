"""
투자자 데이터 처리 모듈
DART 대량보유 공시 기반 기관투자자 프로파일링
13F 스타일 보유 현황 분석 (한국판: 주요주주/기관 공시 기반)
"""
from __future__ import annotations
import re
from typing import Any
from config.settings import MAX_TARGETED_INVESTORS, INVESTOR_SCORE_THRESHOLD

# 샘플 투자자 유형 분류 사전
INVESTOR_TYPE_KEYWORDS = {
    "국민연금": "pension_fund",
    "사학연금": "pension_fund",
    "공무원연금": "pension_fund",
    "교직원공제회": "pension_fund",
    "삼성자산": "asset_manager",
    "미래에셋": "asset_manager",
    "KB자산": "asset_manager",
    "한국투자": "asset_manager",
    "신한자산": "asset_manager",
    "블랙록": "foreign_passive",
    "뱅가드": "foreign_passive",
    "피델리티": "foreign_active",
    "캐피탈": "foreign_active",
    "소버린": "sovereign_wealth",
    "싱가포르": "sovereign_wealth",
    "노르웨이": "sovereign_wealth",
}

# 투자자 스타일별 선호 메시지 포인트
INVESTOR_STYLE_PREFERENCES = {
    "pension_fund": ["장기 수익성", "배당 안정성", "ESG", "거버넌스"],
    "asset_manager": ["밸류에이션", "성장 모멘텀", "섹터 포지션", "유동성"],
    "foreign_passive": ["지수 편입 현황", "시가총액", "유동주식 비율"],
    "foreign_active": ["차별화 전략", "경쟁우위", "경영진 신뢰도", "중장기 가이던스"],
    "sovereign_wealth": ["국가 리스크", "장기 성장 스토리", "지정학적 포지션"],
    "hedge_fund": ["단기 촉매", "이벤트 드리븐", "밸류에이션 갭"],
    "retail": ["브랜드 가치", "주주환원", "쉬운 사업 모델"],
}


def classify_investor_type(investor_name: str) -> str:
    """투자자명으로 유형 분류"""
    for keyword, itype in INVESTOR_TYPE_KEYWORDS.items():
        if keyword in investor_name:
            return itype
    if re.search(r"(펀드|운용|자산|투자)", investor_name):
        return "asset_manager"
    if re.search(r"(은행|증권|보험)", investor_name):
        return "financial_institution"
    return "unknown"


def score_investor_fit(
    investor: dict,
    company_profile: dict,
    narrative_themes: list[str],
) -> float:
    """
    투자자 fit 점수 계산 (0.0 ~ 1.0)
    investor: {name, type, holding_pct, holding_change, last_contact}
    company_profile: {sector, market_cap, dividend_yield, growth_rate, esg_score}
    narrative_themes: 현재 IR 나레이티브 핵심 키워드 목록
    """
    score = 0.0
    itype = investor.get("type", classify_investor_type(investor.get("name", "")))
    preferences = INVESTOR_STYLE_PREFERENCES.get(itype, [])

    # 1. 나레이티브 테마 매칭 (40점)
    matched = sum(1 for t in narrative_themes if any(p in t for p in preferences))
    theme_score = min(matched / max(len(preferences), 1), 1.0) * 0.4
    score += theme_score

    # 2. 보유 변동 (30점) — 최근 매수 증가는 engagement 가능성 높음
    change = investor.get("holding_change_pct", 0.0)
    if change > 1.0:
        score += 0.3
    elif change > 0:
        score += 0.15
    elif change < -2.0:
        score += 0.05  # 매도 중이지만 연락 필요

    # 3. 보유 비중 (20점)
    holding = investor.get("holding_pct", 0.0)
    if holding >= 5.0:
        score += 0.2
    elif holding >= 1.0:
        score += 0.1
    elif holding >= 0.1:
        score += 0.05

    # 4. 최근 미팅 이력 (10점) — 오래될수록 재접촉 우선
    last_contact_days = investor.get("last_contact_days", 365)
    if last_contact_days > 180:
        score += 0.1
    elif last_contact_days > 90:
        score += 0.05

    return round(min(score, 1.0), 3)


def build_investor_profiles(
    large_shareholder_data: list[dict],
    manual_list: list[dict] | None = None,
) -> list[dict]:
    """
    DART 대량보유 공시 데이터 → 투자자 프로파일 목록 생성
    manual_list: 수동으로 추가한 투자자 목록 (CRM 데이터 등)
    """
    profiles: list[dict] = []
    seen_names: set[str] = set()

    for item in large_shareholder_data:
        name = item.get("flr_nm", item.get("name", ""))
        if name in seen_names:
            continue
        seen_names.add(name)

        itype = classify_investor_type(name)
        profiles.append({
            "name": name,
            "type": itype,
            "holding_pct": float(item.get("holding_pct", 0)),
            "holding_change_pct": float(item.get("change_pct", 0)),
            "last_contact_days": item.get("last_contact_days", 180),
            "rcept_no": item.get("rcept_no", ""),
            "source": "dart",
            "preferences": INVESTOR_STYLE_PREFERENCES.get(itype, []),
        })

    # 수동 추가 투자자
    if manual_list:
        for inv in manual_list:
            name = inv.get("name", "")
            if name not in seen_names:
                seen_names.add(name)
                itype = inv.get("type", classify_investor_type(name))
                profiles.append({
                    **inv,
                    "type": itype,
                    "preferences": INVESTOR_STYLE_PREFERENCES.get(itype, []),
                    "source": "manual",
                })

    return profiles


def target_top_investors(
    profiles: list[dict],
    company_profile: dict,
    narrative_themes: list[str],
    top_n: int = MAX_TARGETED_INVESTORS,
    threshold: float = INVESTOR_SCORE_THRESHOLD,
) -> list[dict]:
    """적합도 점수 기반 상위 N명 투자자 선정"""
    scored = []
    for p in profiles:
        score = score_investor_fit(p, company_profile, narrative_themes)
        if score >= threshold:
            scored.append({**p, "fit_score": score})
    scored.sort(key=lambda x: x["fit_score"], reverse=True)
    return scored[:top_n]


def get_sample_investors() -> list[dict]:
    """API 키 없이 테스트용 샘플 투자자 데이터"""
    return [
        {"name": "국민연금공단", "holding_pct": 8.2, "change_pct": 0.3, "last_contact_days": 120},
        {"name": "블랙록", "holding_pct": 5.1, "change_pct": -0.2, "last_contact_days": 200},
        {"name": "미래에셋자산운용", "holding_pct": 3.4, "change_pct": 1.1, "last_contact_days": 45},
        {"name": "피델리티인터내셔널", "holding_pct": 2.7, "change_pct": 0.8, "last_contact_days": 300},
        {"name": "싱가포르투자청(GIC)", "holding_pct": 1.9, "change_pct": 0.0, "last_contact_days": 250},
        {"name": "한국투자신탁운용", "holding_pct": 1.5, "change_pct": -0.5, "last_contact_days": 60},
        {"name": "노르웨이국부펀드", "holding_pct": 1.2, "change_pct": 0.1, "last_contact_days": 400},
        {"name": "KB자산운용", "holding_pct": 0.9, "change_pct": 0.4, "last_contact_days": 90},
        {"name": "삼성자산운용", "holding_pct": 0.8, "change_pct": 0.2, "last_contact_days": 30},
        {"name": "캐피탈그룹", "holding_pct": 0.7, "change_pct": -0.1, "last_contact_days": 180},
    ]
