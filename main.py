"""
CLI 진입점
실행: python main.py --company-code 005930 --company-name 삼성전자
"""
from __future__ import annotations
import argparse
import json
import sys
from config.settings import DEFAULT_COMPANY_CODE, DEFAULT_COMPANY_NAME, validate_keys
from graph.workflow import run_workflow, resume_workflow


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Proactive Strategy & Investor Intelligence Loop CLI"
    )
    parser.add_argument("--company-code", default=DEFAULT_COMPANY_CODE, help="DART 종목코드")
    parser.add_argument("--company-name", default=DEFAULT_COMPANY_NAME, help="기업명")
    parser.add_argument("--auto-approve", action="store_true", help="Human 승인 자동 처리 (테스트용)")
    parser.add_argument("--output", default=None, help="결과 JSON 저장 경로")
    args = parser.parse_args()

    # API 키 확인
    keys = validate_keys()
    missing = [k for k, ok in keys.items() if not ok and k != "TAVILY_API_KEY"]
    if missing:
        print(f"[경고] 미설정 API 키: {', '.join(missing)}")
        print(".env 파일에 API 키를 입력하세요. (샘플 데이터로 계속 진행)")

    print(f"\n{'='*60}")
    print(f"  IR Intelligence Loop 시작")
    print(f"  기업: {args.company_name} ({args.company_code})")
    print(f"{'='*60}\n")

    # 1단계: Human approval 전까지 실행
    print("[1/2] 워크플로우 실행 중 (모니터링 → 나레이티브 → 타깃팅 → 최적화)...")
    chunks, thread_id = run_workflow(args.company_code, args.company_name)
    state = _extract_state(chunks)

    # 상태 요약 출력
    _print_summary(state)

    # 2단계: Human approval
    if state.get("current_step") == "awaiting_human_approval":
        if args.auto_approve:
            print("\n[auto-approve] 자동 승인 처리...")
            approval = "approved"
            reason = ""
        else:
            print("\n" + "="*60)
            print("  ⏸️  나레이티브 검토 후 승인/반려 입력")
            print("="*60)
            narrative = state.get("narrative_draft", "")
            print("\n[나레이티브 미리보기]\n")
            print(narrative[:1000])
            print("\n...")
            print("\n[컴플라이언스]", "통과" if state.get("compliance_passed") else "이슈 있음")
            for flag in state.get("compliance_flags", []):
                print(f"  • {flag}")
            print()
            choice = input("승인하시겠습니까? (y=승인 / n=반려): ").strip().lower()
            approval = "approved" if choice == "y" else "rejected"
            reason = ""
            if approval == "rejected":
                reason = input("반려 사유 입력: ").strip()

        print(f"\n[2/2] 워크플로우 재개 ({approval})...")
        final_chunks = resume_workflow(thread_id, approval, reason)
        final_state = _extract_state(final_chunks)
        state.update(final_state)

    # 결과 저장
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n결과 저장: {args.output}")

    # 최종 요약
    final_step = state.get("current_step", "unknown")
    print(f"\n{'='*60}")
    print(f"  완료: {final_step}")
    print(f"  타깃 투자자: {len(state.get('targeted_investors', []))}명")
    print(f"  개인화 메시지: {len(state.get('personalized_messages', []))}건")
    print(f"  컴플라이언스: {'통과' if state.get('compliance_passed') else '이슈'}")
    print(f"{'='*60}\n")
    print("Streamlit 대시보드를 보려면: streamlit run app.py")


def _extract_state(chunks: dict) -> dict:
    merged = {}
    for _, node_state in chunks.items():
        if isinstance(node_state, dict):
            merged.update(node_state)
    return merged


def _print_summary(state: dict) -> None:
    gaps = state.get("strategy_gaps", [])
    print(f"\n  탐지된 Gap: {len(gaps)}개")
    for i, gap in enumerate(gaps[:5], 1):
        print(f"    {i}. {gap}")
    print(f"\n  나레이티브 생성: {'완료' if state.get('narrative_draft') else '미완료'}")
    print(f"  타깃 투자자: {len(state.get('targeted_investors', []))}명")
    print(f"  컴플라이언스: {'통과' if state.get('compliance_passed') else '이슈'}")
    print()


if __name__ == "__main__":
    main()
