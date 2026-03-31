"""
LangGraph StateGraph 워크플로우 정의

그래프 흐름:
START
  → supervisor
  → monitoring_agent
  → narrative_generator
  → profile_targeting
  → personalization
  → optimization
  → human_approval (interrupt here)
  → [approved] → feedback_loop → END
  → [rejected]  → narrative_generator (재생성, 최대 MAX_ITERATIONS)
  → [error]     → error_handler → END

Mermaid:
```mermaid
graph TD
    START --> supervisor
    supervisor --> monitoring
    monitoring --> narrative_generator
    narrative_generator --> profile_targeting
    profile_targeting --> personalization
    personalization --> optimization
    optimization --> human_approval
    human_approval -->|approved| feedback_loop
    human_approval -->|rejected| narrative_generator
    human_approval -->|error/max| error_handler
    feedback_loop --> END
    error_handler --> END
```
"""
from __future__ import annotations
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import IRState, initial_state
from agents.supervisor import (
    supervisor_agent,
    route_after_monitoring,
    route_after_narrative,
    route_after_optimization,
    route_after_human_approval,
    feedback_loop_agent,
    error_handler,
)
from agents.monitoring import monitoring_agent
from agents.narrative_generator import narrative_generator_agent
from agents.profile_targeting import profile_targeting_agent
from agents.personalization import personalization_agent
from agents.optimization import optimization_agent


def _human_approval_node(state: IRState) -> IRState:
    """
    Human-in-the-loop 게이트 노드.
    LangGraph의 interrupt_before 메커니즘으로 여기서 실행이 일시 중단된다.
    Streamlit에서 승인/반려 버튼을 누르면 state를 업데이트하고 resume.
    """
    return {**state, "current_step": "awaiting_human_approval"}


def build_graph() -> StateGraph:
    """StateGraph 빌드 및 반환"""
    builder = StateGraph(IRState)

    # ── 노드 등록 ──────────────────────────────────────────
    builder.add_node("supervisor", supervisor_agent)
    builder.add_node("monitoring", monitoring_agent)
    builder.add_node("narrative_generator", narrative_generator_agent)
    builder.add_node("profile_targeting", profile_targeting_agent)
    builder.add_node("personalization", personalization_agent)
    builder.add_node("optimization", optimization_agent)
    builder.add_node("human_approval", _human_approval_node)
    builder.add_node("feedback_loop", feedback_loop_agent)
    builder.add_node("error_handler", error_handler)

    # ── 엣지 연결 ─────────────────────────────────────────
    builder.set_entry_point("supervisor")
    builder.add_edge("supervisor", "monitoring")

    builder.add_conditional_edges(
        "monitoring",
        route_after_monitoring,
        {
            "narrative_generator": "narrative_generator",
            "end_with_error": "error_handler",
        },
    )

    builder.add_conditional_edges(
        "narrative_generator",
        route_after_narrative,
        {
            "profile_targeting": "profile_targeting",
            "end_with_error": "error_handler",
        },
    )

    builder.add_edge("profile_targeting", "personalization")
    builder.add_edge("personalization", "optimization")

    builder.add_conditional_edges(
        "optimization",
        route_after_optimization,
        {
            "human_approval": "human_approval",
        },
    )

    builder.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {
            "feedback_loop": "feedback_loop",
            "narrative_generator": "narrative_generator",
            "human_approval": "human_approval",
            "end_with_error": "error_handler",
        },
    )

    builder.add_edge("feedback_loop", END)
    builder.add_edge("error_handler", END)

    return builder


def create_compiled_graph(checkpointer=None):
    """
    컴파일된 그래프 반환.
    interrupt_before=["human_approval"]로 HIL 게이트 설정.
    """
    builder = build_graph()
    if checkpointer is None:
        checkpointer = MemorySaver()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"],
    )


def run_workflow(
    company_code: str,
    company_name: str,
    thread_id: str | None = None,
) -> tuple[dict, str]:
    """
    워크플로우 실행 진입점.
    Returns: (최종 상태, thread_id)
    Human approval 전까지 실행 후 일시 중단.
    """
    import uuid
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    graph = create_compiled_graph()
    state = initial_state(company_code, company_name)
    config = {"configurable": {"thread_id": thread_id}}

    # Human approval 전까지 실행
    final_state = None
    for chunk in graph.stream(state, config=config):
        final_state = chunk

    return final_state or {}, thread_id


def resume_workflow(
    thread_id: str,
    approval: str,
    rejection_reason: str = "",
) -> dict:
    """
    Human approval 후 워크플로우 재개.
    approval: "approved" | "rejected"
    """
    graph = create_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # 상태 업데이트: approval 결과 주입
    graph.update_state(
        config,
        {
            "human_approval": approval,
            "rejection_reason": rejection_reason,
        },
    )

    # 재개 실행
    final_state = None
    for chunk in graph.stream(None, config=config):
        final_state = chunk

    return final_state or {}
