"""
메인 Streamlit 대시보드
탭 구성:
  1. Gap 알림 & 모니터링
  2. 나레이티브 & 브리핑팩
  3. 투자자 타깃팅 & 개인화 메시지
  4. 컴플라이언스 & Audit Trail
  5. 자연어 질의
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config.settings import DEFAULT_COMPANY_CODE, DEFAULT_COMPANY_NAME, validate_keys
from graph.workflow import run_workflow, resume_workflow
from graph.state import initial_state
from ui.components.alerts import render_alerts_tab
from ui.components.briefing import render_briefing_tab
from ui.components.query import render_query_tab
from utils.audit import load_audit_logs
from utils.helpers import sentiment_to_emoji, now_str


def render_dashboard() -> None:
    """메인 대시보드 렌더링"""
    st.set_page_config(
        page_title="IR Intelligence Loop",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _render_sidebar()

    st.title("📈 Proactive Strategy & Investor Intelligence Loop")
    st.caption(f"한국 상장사 IR 멀티 에이전트 시스템 | 현재 시각: {now_str()}")

    # 상태 가져오기
    ir_state = st.session_state.get("ir_state", {})
    current_step = ir_state.get("current_step", "")

    # ── Human Approval Gate ────────────────────────────────
    if current_step == "awaiting_human_approval":
        _render_human_approval_gate(ir_state)
        st.divider()

    # ── 진행 상태 표시 ────────────────────────────────────
    if ir_state:
        _render_progress_bar(current_step)

    # ── 메인 탭 ──────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📡 모니터링 & Gap",
        "📦 브리핑팩",
        "🎯 투자자 타깃팅",
        "✅ 컴플라이언스",
        "💬 자연어 질의",
    ])

    with tab1:
        render_alerts_tab(ir_state)

    with tab2:
        render_briefing_tab(ir_state)

    with tab3:
        _render_targeting_tab(ir_state)

    with tab4:
        _render_compliance_tab(ir_state)

    with tab5:
        render_query_tab(ir_state)


def _render_sidebar() -> None:
    """사이드바: 기업 입력 & 워크플로우 실행"""
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/stock-share.png", width=60)
        st.title("IR 설정")

        # API 키 상태 표시
        keys = validate_keys()
        for key, ok in keys.items():
            icon = "🟢" if ok else "🔴"
            st.caption(f"{icon} {key}")

        st.divider()

        # 기업 정보 입력
        company_name = st.text_input("기업명", value=DEFAULT_COMPANY_NAME, key="company_name_input")
        company_code = st.text_input("종목코드", value=DEFAULT_COMPANY_CODE, key="company_code_input")

        st.divider()

        # 워크플로우 실행 버튼
        run_btn = st.button("🚀 분석 시작", type="primary", use_container_width=True)
        if run_btn:
            if not company_name or not company_code:
                st.error("기업명과 종목코드를 입력하세요.")
            else:
                _run_workflow(company_code, company_name)

        # 초기화
        if st.button("🔄 초기화", use_container_width=True):
            for key in ["ir_state", "thread_id", "chat_history"]:
                st.session_state.pop(key, None)
            st.rerun()

        st.divider()

        # 현재 상태 요약
        ir_state = st.session_state.get("ir_state", {})
        if ir_state:
            step = ir_state.get("current_step", "")
            st.caption(f"**현재 단계:** {step}")
            st.caption(f"**Gap 수:** {len(ir_state.get('strategy_gaps', []))}")
            st.caption(f"**타깃 투자자:** {len(ir_state.get('targeted_investors', []))}명")
            iteration = ir_state.get("iteration_count", 0)
            if iteration:
                st.caption(f"**재생성 횟수:** {iteration}회")


def _run_workflow(company_code: str, company_name: str) -> None:
    """워크플로우 실행"""
    with st.spinner(f"{company_name} 분석 중... (수십 초 소요)"):
        try:
            final_chunks, thread_id = run_workflow(company_code, company_name)
            # 마지막 노드 상태 추출
            state = _extract_state_from_chunks(final_chunks)
            st.session_state["ir_state"] = state
            st.session_state["thread_id"] = thread_id
            step = state.get("current_step", "")
            if step == "awaiting_human_approval":
                st.success("분석 완료. 나레이티브를 검토하고 승인/반려해 주세요.")
            else:
                st.success(f"완료: {step}")
        except Exception as e:
            st.error(f"오류 발생: {e}")
    st.rerun()


def _extract_state_from_chunks(chunks: dict) -> dict:
    """LangGraph stream 결과에서 최신 상태 추출"""
    if not chunks:
        return {}
    # stream은 {node_name: state_update} dict를 반환
    # 마지막 노드의 상태를 합산
    merged = {}
    for node_name, node_state in chunks.items():
        if isinstance(node_state, dict):
            merged.update(node_state)
    return merged


def _render_human_approval_gate(state: dict) -> None:
    """Human-in-the-loop 승인 게이트 UI"""
    st.warning("### ⏸️ 승인 대기 중")
    st.write("IR 나레이티브가 생성되었습니다. 검토 후 승인 또는 반려해 주세요.")

    narrative_preview = state.get("narrative_draft", "")[:600]
    st.markdown(f"**나레이티브 미리보기:**\n\n{narrative_preview}...")

    compliance_passed = state.get("compliance_passed", False)
    compliance_flags = state.get("compliance_flags", [])
    if compliance_passed:
        st.success("✅ 컴플라이언스 검사 통과")
    else:
        st.error(f"❌ 컴플라이언스 이슈 {len(compliance_flags)}개 — 수정 권고")
        for flag in compliance_flags:
            st.caption(f"  • {flag}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 승인", type="primary", key="approve_btn"):
            _resume(approval="approved")

    with col2:
        rejection_reason = st.text_input("반려 사유 (선택)", key="rejection_input")
        if st.button("❌ 반려 (재생성)", type="secondary", key="reject_btn"):
            _resume(approval="rejected", rejection_reason=rejection_reason)


def _resume(approval: str, rejection_reason: str = "") -> None:
    """워크플로우 재개"""
    thread_id = st.session_state.get("thread_id")
    if not thread_id:
        st.error("Thread ID 없음. 다시 실행해 주세요.")
        return
    with st.spinner("처리 중..."):
        try:
            chunks = resume_workflow(thread_id, approval, rejection_reason)
            state = _extract_state_from_chunks(chunks)
            # 기존 상태와 병합
            existing = st.session_state.get("ir_state", {})
            existing.update(state)
            st.session_state["ir_state"] = existing
        except Exception as e:
            st.error(f"재개 오류: {e}")
    st.rerun()


def _render_progress_bar(current_step: str) -> None:
    """워크플로우 진행 단계 표시"""
    steps = [
        ("supervisor_init", "초기화"),
        ("monitoring_complete", "모니터링"),
        ("narrative_generated", "나레이티브"),
        ("targeting_complete", "타깃팅"),
        ("personalization_complete", "개인화"),
        ("optimization_complete", "최적화"),
        ("awaiting_human_approval", "승인 대기"),
        ("completed", "완료"),
    ]
    step_names = [s[0] for s in steps]
    step_labels = [s[1] for s in steps]
    current_idx = next(
        (i for i, s in enumerate(step_names) if s == current_step), 0
    )
    progress = (current_idx + 1) / len(steps)
    st.progress(progress, text=f"단계: {step_labels[current_idx]} ({current_idx+1}/{len(steps)})")


def _render_targeting_tab(state: dict) -> None:
    """탭 3: 투자자 타깃팅 & 개인화"""
    st.header("🎯 투자자 타깃팅 & 개인화 메시지")

    targeted = state.get("targeted_investors", [])
    messages = state.get("personalized_messages", [])

    if not targeted:
        st.info("아직 투자자 타깃팅이 완료되지 않았습니다.")
        return

    # ── 타깃 투자자 테이블 ────────────────────────────────
    st.subheader("🏆 타깃 투자자 목록")
    df = pd.DataFrame([
        {
            "기관명": t.get("name", ""),
            "유형": t.get("type", ""),
            "보유비중(%)": t.get("holding_pct", 0),
            "보유변동(%)": t.get("holding_change_pct", 0),
            "Fit 점수": t.get("fit_score", 0),
        }
        for t in targeted
    ])
    st.dataframe(
        df.style.background_gradient(subset=["Fit 점수"], cmap="YlGn"),
        use_container_width=True,
        hide_index=True,
    )

    # ── 투자자 유형 파이차트 ──────────────────────────────
    if targeted:
        type_counts = df["유형"].value_counts().reset_index()
        type_counts.columns = ["유형", "수"]
        fig = px.pie(type_counts, values="수", names="유형", title="타깃 투자자 유형 분포")
        st.plotly_chart(fig, use_container_width=True)

    # ── Fit 점수 바차트 ───────────────────────────────────
    if len(targeted) > 1:
        fig2 = px.bar(
            df.sort_values("Fit 점수", ascending=True),
            x="Fit 점수", y="기관명",
            orientation="h",
            title="투자자 Fit 점수",
            color="Fit 점수",
            color_continuous_scale="blues",
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── 개인화 메시지 ─────────────────────────────────────
    st.subheader("✉️ 개인화 메시지")
    if not messages:
        st.info("개인화 메시지가 아직 생성되지 않았습니다.")
        return

    for msg in messages:
        investor_name = msg.get("investor_name", "")
        fit_score = msg.get("fit_score", 0)
        engagement_context = msg.get("engagement_context", "")

        with st.expander(f"📧 {investor_name} | Fit: {fit_score:.2f} | {engagement_context}"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("**미팅 초청 이메일:**")
                st.text_area(
                    "",
                    value=msg.get("email", ""),
                    height=150,
                    key=f"email_{investor_name}",
                )
            with col2:
                st.markdown("**미팅 어젠다:**")
                agenda = msg.get("agenda", [])
                for item in agenda:
                    st.write(f"• {item}")

            st.markdown("**핵심 메시지:**")
            for km in msg.get("key_messages", []):
                st.info(km)


def _render_compliance_tab(state: dict) -> None:
    """탭 4: 컴플라이언스 & Audit Trail"""
    st.header("✅ 컴플라이언스 & Audit Trail")

    # ── 컴플라이언스 현황 ─────────────────────────────────
    st.subheader("📋 컴플라이언스 검사 결과")
    passed = state.get("compliance_passed", False)
    flags = state.get("compliance_flags", [])

    if not state.get("narrative_draft"):
        st.info("아직 컴플라이언스 검사가 실행되지 않았습니다.")
    elif passed:
        st.success("✅ 모든 컴플라이언스 검사 통과 — 배포 승인 가능")
    else:
        st.error(f"❌ {len(flags)}개 이슈 발견")
        for flag in flags:
            st.warning(flag)

    st.divider()

    # ── Audit Trail ────────────────────────────────────
    st.subheader("🔍 현재 세션 Audit Trail")
    trail = state.get("audit_trail", [])
    if trail:
        df = pd.DataFrame([
            {
                "시각": t.get("timestamp", "")[:19],
                "에이전트": t.get("agent", ""),
                "액션": t.get("action", ""),
                "단계": t.get("step", ""),
            }
            for t in trail
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Audit 기록 없음")

    st.divider()

    # ── 이전 세션 로그 ────────────────────────────────────
    st.subheader("📂 이전 세션 Audit 로그")
    logs = load_audit_logs(n=5)
    if logs:
        for log in logs:
            session_id = log.get("session_id", "unknown")
            timestamp = log.get("timestamp", "")[:16]
            company = log.get("company", "")
            kpis = log.get("kpis", {})
            with st.expander(f"📁 {company} | {timestamp} | {session_id}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Gap 해소율", f"{kpis.get('gap_coverage_rate', 0):.0%}")
                    st.metric("타깃 투자자", kpis.get("targeted_investor_count", 0))
                with col2:
                    st.metric("Avg Fit Score", f"{kpis.get('avg_investor_fit_score', 0):.2f}")
                    st.metric("컴플라이언스", "통과" if kpis.get("compliance_passed") else "이슈")
                compliance_info = log.get("compliance", {})
                if compliance_info.get("flags"):
                    st.caption("이슈: " + "; ".join(compliance_info["flags"][:2]))
    else:
        st.info("이전 세션 로그 없음")
