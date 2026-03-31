"""
Personalization & Engagement Agent
타깃 투자자별 맞춤 메시지, NDR 어젠다, 미팅 자료 생성
"""
from __future__ import annotations
import json
import re
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY, LLM_MODEL
from graph.state import IRState
from tools.investor_data import INVESTOR_STYLE_PREFERENCES
from utils.audit import record_action

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def personalization_agent(state: IRState) -> IRState:
    """
    4단계: 투자자별 맞춤 메시지 & 미팅 어젠다 생성
    """
    company_name = state["company_name"]
    targeted = state.get("targeted_investors", [])
    narrative = state.get("narrative_draft", "")
    qa_pairs = state.get("qa_pairs", [])

    record_action(state, "personalization_agent", "start", {
        "targeted_count": len(targeted),
    })

    personalized_messages: list[dict] = []

    for investor in targeted[:5]:  # 상위 5명 개인화 (토큰 절약)
        msg = _generate_personalized_message(
            investor, company_name, narrative, qa_pairs
        )
        personalized_messages.append(msg)

    record_action(state, "personalization_agent", "complete", {
        "messages_generated": len(personalized_messages),
    })

    return {
        **state,
        "personalized_messages": personalized_messages,
        "current_step": "personalization_complete",
    }


def _generate_personalized_message(
    investor: dict,
    company_name: str,
    narrative: str,
    qa_pairs: list[dict],
) -> dict:
    """투자자 1인에 대한 맞춤 메시지 생성"""
    investor_name = investor.get("name", "투자자")
    investor_type = investor.get("type", "unknown")
    holding_pct = investor.get("holding_pct", 0)
    holding_change = investor.get("holding_change_pct", 0)
    fit_score = investor.get("fit_score", 0.5)
    preferences = investor.get("preferences", INVESTOR_STYLE_PREFERENCES.get(investor_type, []))

    # 보유 변동 상태
    if holding_change > 0.5:
        engagement_context = "최근 보유 비중 증가 — 추가 매수 관심 투자자"
    elif holding_change < -1.0:
        engagement_context = "최근 보유 비중 감소 — 우려 사항 해소 필요"
    else:
        engagement_context = "안정적 보유 — 신뢰 관계 유지"

    prompt = f"""당신은 {company_name}의 IR 담당자입니다.
다음 투자자에게 개인화된 IR 미팅 초청 메일과 미팅 어젠다를 작성하세요.

## 투자자 정보
- 기관명: {investor_name}
- 투자자 유형: {investor_type}
- 보유 비중: {holding_pct}%
- 최근 보유 변동: {holding_change:+.1f}%
- 상황: {engagement_context}
- 관심 포인트: {', '.join(preferences[:4])}
- Fit 점수: {fit_score:.2f}/1.0

## IR 나레이티브 핵심 (요약)
{narrative[:800]}

## 요청
1. 미팅 초청 이메일 (한국어, 200자 이내, 격식체)
2. 미팅 어젠다 (30분 기준, bullet point)
3. 해당 투자자 맞춤 핵심 메시지 3가지 (투자자 관심사 기반)

JSON 형식으로만 응답:
{{
  "email": "...",
  "agenda": ["...", "..."],
  "key_messages": ["...", "...", "..."]
}}"""

    try:
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            content = json.loads(match.group())
        else:
            content = _fallback_message(investor_name, preferences)
    except Exception:
        content = _fallback_message(investor_name, preferences)

    return {
        "investor_name": investor_name,
        "investor_type": investor_type,
        "fit_score": fit_score,
        "holding_pct": holding_pct,
        "holding_change_pct": holding_change,
        "engagement_context": engagement_context,
        **content,
    }


def _fallback_message(investor_name: str, preferences: list[str]) -> dict:
    return {
        "email": f"{investor_name} 귀중,\n\n당사 IR 미팅에 초청드립니다. 최근 경영 현황과 중장기 전략을 공유드리고자 하며, 귀사의 소중한 의견을 듣고 싶습니다. 일정을 조율해 주시면 감사하겠습니다.\n\n감사합니다.",
        "agenda": [
            "경영 현황 및 최근 실적 브리핑 (10분)",
            "중장기 전략 방향성 공유 (10분)",
            "Q&A 및 자유 토론 (10분)",
        ],
        "key_messages": [
            f"{', '.join(preferences[:2])} 중심 가치 제고",
            "안정적 수익성 및 성장 모멘텀 지속",
            "주주 친화적 정책 강화",
        ],
    }
