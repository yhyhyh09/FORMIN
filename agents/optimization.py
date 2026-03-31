"""
Optimization & Compliance Agent
컴플라이언스 검사, KPI 추적, 메시지 최적화, audit trail 마무리
"""
from __future__ import annotations
from datetime import datetime
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY, LLM_MODEL
from graph.state import IRState
from tools.compliance import run_full_compliance_check
from utils.audit import record_action, save_audit_log

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def optimization_agent(state: IRState) -> IRState:
    """
    5단계: 컴플라이언스 검사 + 메시지 최적화 + KPI 계산
    """
    company_name = state["company_name"]
    narrative = state.get("narrative_draft", "")
    messages = state.get("personalized_messages", [])
    targeted = state.get("targeted_investors", [])
    gaps = state.get("strategy_gaps", [])

    record_action(state, "optimization_agent", "start", {})

    # ── 컴플라이언스 검사 ─────────────────────────────────
    compliance_result = run_full_compliance_check(narrative, messages)
    compliance_flags = compliance_result.get("flags", [])
    compliance_passed = compliance_result.get("passed", False)

    # ── KPI 계산 ──────────────────────────────────────────
    kpis = _calculate_kpis(state, compliance_result)

    # ── 최적화 제안 (LLM) ────────────────────────────────
    optimization_notes = []
    if not compliance_passed:
        optimization_notes = _suggest_optimizations(narrative, compliance_flags)

    # ── audit trail 저장 ──────────────────────────────────
    full_audit = {
        "session_id": f"{company_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "company": company_name,
        "timestamp": datetime.now().isoformat(),
        "kpis": kpis,
        "compliance": compliance_result,
        "optimization_notes": optimization_notes,
        "trail": state.get("audit_trail", []),
    }
    save_audit_log(full_audit)

    record_action(state, "optimization_agent", "complete", {
        "compliance_passed": compliance_passed,
        "flags": len(compliance_flags),
        "kpis": kpis,
    })

    return {
        **state,
        "compliance_flags": compliance_flags,
        "compliance_passed": compliance_passed,
        "current_step": "optimization_complete",
        "messages": [{
            "role": "assistant",
            "content": (
                f"컴플라이언스: {'통과' if compliance_passed else f'{len(compliance_flags)}개 이슈'}\n"
                f"KPI: {kpis}\n"
                f"최적화 제안: {optimization_notes[:2] if optimization_notes else '없음'}"
            ),
        }],
    }


def _calculate_kpis(state: IRState, compliance_result: dict) -> dict:
    """IR 준비 품질 KPI 계산"""
    gaps = state.get("strategy_gaps", [])
    targeted = state.get("targeted_investors", [])
    messages = state.get("personalized_messages", [])
    narrative = state.get("narrative_draft", "")
    qa_pairs = state.get("qa_pairs", [])

    # Gap 해소율: 나레이티브에서 Gap 키워드가 언급된 비율
    addressed = sum(1 for gap in gaps if any(kw in narrative for kw in gap.split()[:3]))
    gap_coverage = round(addressed / len(gaps), 2) if gaps else 1.0

    # 평균 투자자 fit score
    avg_fit = round(
        sum(t.get("fit_score", 0) for t in targeted) / len(targeted), 3
    ) if targeted else 0.0

    return {
        "gap_coverage_rate": gap_coverage,
        "gaps_detected": len(gaps),
        "gaps_addressed": addressed,
        "targeted_investor_count": len(targeted),
        "avg_investor_fit_score": avg_fit,
        "personalized_message_count": len(messages),
        "qa_pair_count": len(qa_pairs),
        "narrative_word_count": len(narrative.split()),
        "compliance_flags": compliance_result.get("flag_count", 0),
        "compliance_passed": compliance_result.get("passed", False),
    }


def _suggest_optimizations(narrative: str, flags: list[str]) -> list[str]:
    """컴플라이언스 이슈에 대한 수정 제안 생성"""
    if not flags:
        return []
    flag_text = "\n".join(f"- {f}" for f in flags[:5])
    prompt = f"""아래 컴플라이언스 이슈에 대한 구체적인 수정 방향을 제안하세요.

## 이슈 목록
{flag_text}

각 이슈에 대해 1~2문장으로 수정 방향을 제시하세요. 한국어로.
번호 목록 형식으로만 응답."""
    try:
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        lines = [l.strip() for l in text.split("\n") if l.strip() and l[0].isdigit()]
        return lines
    except Exception:
        return [f"이슈 수정 필요: {f}" for f in flags[:3]]
