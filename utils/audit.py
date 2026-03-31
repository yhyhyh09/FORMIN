"""
Audit Trail 모듈
모든 에이전트 액션을 타임스탬프 포함 JSON 로그로 기록
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from config.settings import AUDIT_LOG_DIR


def record_action(state: dict, agent: str, action: str, metadata: dict | None = None) -> None:
    """
    상태의 audit_trail에 액션 기록 (in-memory)
    state는 dict이므로 직접 append
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "action": action,
        "step": state.get("current_step", "unknown"),
        "metadata": metadata or {},
    }
    # LangGraph 상태는 불변 업데이트가 원칙이나
    # audit_trail은 append reducer를 사용하므로 반환 시 포함
    # 여기서는 직접 추가 (노드 반환 dict에 포함됨)
    trail = state.get("audit_trail", [])
    trail.append(entry)


def save_audit_log(audit_data: dict) -> Path:
    """
    전체 audit 데이터를 JSON 파일로 저장
    파일명: {company}_{timestamp}.json
    """
    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    session_id = audit_data.get("session_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
    filename = AUDIT_LOG_DIR / f"{session_id}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)
    return filename


def load_audit_logs(n: int = 10) -> list[dict]:
    """최근 N개 audit 로그 파일 로드"""
    files = sorted(AUDIT_LOG_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    logs = []
    for f in files[:n]:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                logs.append(json.load(fp))
        except Exception:
            continue
    return logs
