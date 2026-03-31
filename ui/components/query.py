"""
Natural Language Query 컴포넌트
IR 담당자가 자연어로 Claude에게 직접 질의
"""
from __future__ import annotations
import streamlit as st
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY, LLM_MODEL

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def render_query_tab(state: dict) -> None:
    """탭 5: 자연어 질의"""
    st.header("💬 IR 어시스턴트 질의")
    st.caption("나레이티브, 투자자 데이터, 컴플라이언스 등 IR 관련 질문을 자유롭게 입력하세요.")

    # 세션 히스토리 초기화
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 컨텍스트 요약 (현재 state 기반)
    context_summary = _build_context(state)

    # 대화 히스토리 표시
    for msg in st.session_state.chat_history:
        role = msg["role"]
        with st.chat_message(role):
            st.markdown(msg["content"])

    # 입력창
    user_input = st.chat_input("질문 입력 (예: '국민연금에게 어떤 메시지가 가장 적합한가요?')")

    if user_input:
        # 사용자 메시지 추가
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Claude 응답
        with st.chat_message("assistant"):
            with st.spinner("분석 중..."):
                response = _query_claude(user_input, context_summary, st.session_state.chat_history)
            st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})

    # 초기화 버튼
    if st.button("대화 초기화"):
        st.session_state.chat_history = []
        st.rerun()

    # 예시 질문
    with st.expander("💡 예시 질문"):
        st.markdown("""
- 현재 IR 나레이티브에서 가장 약한 부분은 어디인가요?
- 국민연금 대상 핵심 메시지 3가지를 제안해 주세요.
- 최근 부정 뉴스에 어떻게 대응하면 좋을까요?
- 외국계 액티브 펀드가 관심 가질 포인트는?
- 이번 분기 실적 발표 전 IR 전략은?
- 경쟁사 대비 차별화 포인트를 강조하는 방법은?
""")


def _build_context(state: dict) -> str:
    """현재 IR 상태를 컨텍스트 요약으로 변환"""
    company = state.get("company_name", "기업")
    gaps = state.get("strategy_gaps", [])
    targeted = state.get("targeted_investors", [])
    narrative = state.get("narrative_draft", "")
    compliance_flags = state.get("compliance_flags", [])

    gap_text = "; ".join(gaps[:5]) if gaps else "없음"
    investor_text = ", ".join(
        f"{t.get('name','')}({t.get('type','')})" for t in targeted[:5]
    ) if targeted else "없음"
    compliance_text = "; ".join(compliance_flags[:3]) if compliance_flags else "이슈 없음"

    return f"""## 현재 IR 상태 컨텍스트
- 기업: {company}
- 탐지된 Gap: {gap_text}
- 주요 타깃 투자자: {investor_text}
- 컴플라이언스 이슈: {compliance_text}
- 나레이티브 요약 (앞 500자): {narrative[:500]}
"""


def _query_claude(user_input: str, context: str, history: list[dict]) -> str:
    """Claude에게 IR 컨텍스트 기반 질의"""
    system_prompt = f"""당신은 15년 경력의 한국 상장사 IR/경영전략 전문가입니다.
아래 현재 IR 분석 상태를 기반으로 IR 담당자의 질문에 답변하세요.
답변은 실무적이고 구체적으로, 한국어로 작성하세요.

{context}"""

    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history[-10:]  # 최근 10개 메시지만
        if m["role"] in ("user", "assistant")
    ]

    try:
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        return f"오류가 발생했습니다: {str(e)}\n\nAnthropic API 키를 확인해 주세요."
