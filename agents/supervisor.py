"""
Supervisor / Orchestrator Agent
워크플로우 라우팅, 에러 복구, Human-in-the-loop 조건 결정
"""
from __future__ import annotations
from graph.state import IRState
from config.settings import MAX_ITERATIONS
from utils.audit import record_action


def supervisor_agent(state: IRState) -> IRState:
    """
    그래프 시작 시 상태 초기화 및 입력 유효성 검사
    """
    record_action(state, "supervisor_agent", "init", {
        "company": state.get("company_name"),
        "code": state.get("company_code"),
    })
    return {
        **state,
        "current_step": "supervisor_init",
        "iteration_count": state.get("iteration_count", 0),
        "error": None,
    }


def route_after_monitoring(state: IRState) -> str:
    """모니터링 완료 후 라우팅"""
    if state.get("error"):
        return "end_with_error"
    gaps = state.get("strategy_gaps", [])
    if not gaps:
        # Gap 없으면 간단 보고서만
        return "narrative_generator"
    return "narrative_generator"


def route_after_narrative(state: IRState) -> str:
    """나레이티브 생성 후 라우팅"""
    if state.get("error"):
        return "end_with_error"
    return "profile_targeting"


def route_after_optimization(state: IRState) -> str:
    """최적화 완료 후 라우팅 — HIL 게이트"""
    # 컴플라이언스 실패 시 자동 반려 처리
    if not state.get("compliance_passed", False):
        flags = state.get("compliance_flags", [])
        record_action(state, "supervisor_agent", "auto_reject_compliance", {"flags": flags})
    return "human_approval"


def route_after_human_approval(state: IRState) -> str:
    """Human approval 결과에 따른 라우팅"""
    approval = state.get("human_approval")
    iteration = state.get("iteration_count", 0)

    if approval == "approved":
        record_action(state, "supervisor_agent", "approved", {"iteration": iteration})
        return "feedback_loop"

    if approval == "rejected":
        if iteration >= MAX_ITERATIONS:
            record_action(state, "supervisor_agent", "max_iterations_reached", {"iteration": iteration})
            return "end_with_error"
        record_action(state, "supervisor_agent", "rejected_retry", {"iteration": iteration})
        return "narrative_generator"

    # approval이 None이면 대기 (LangGraph interrupt)
    return "human_approval"


def feedback_loop_agent(state: IRState) -> IRState:
    """
    피드백 루프: 승인된 결과를 최종 상태로 마무리
    """
    record_action(state, "feedback_loop", "finalized", {
        "iteration": state.get("iteration_count"),
        "investors_targeted": len(state.get("targeted_investors", [])),
        "messages_ready": len(state.get("personalized_messages", [])),
    })
    return {
        **state,
        "current_step": "completed",
    }


def error_handler(state: IRState) -> IRState:
    """에러 상태 최종 처리"""
    record_action(state, "error_handler", "error_finalized", {
        "error": state.get("error"),
        "step": state.get("current_step"),
    })
    return {
        **state,
        "current_step": "error",
    }
