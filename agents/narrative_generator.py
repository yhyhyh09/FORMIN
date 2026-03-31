"""
Scenario & Narrative Generator Agent
Gap 분석 결과를 바탕으로 IR 나레이티브, Q&A, 브리핑팩 생성
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, MAX_ITERATIONS
from graph.state import IRState
from utils.audit import record_action

client = Anthropic(api_key=ANTHROPIC_API_KEY)

NARRATIVE_SYSTEM_PROMPT = """당신은 15년 경력의 한국 상장사 IR/경영전략 전문가입니다.
투자자와의 효과적인 소통을 위한 IR 나레이티브를 작성합니다.
- 사실에 기반한 전략적 스토리텔링
- 자본시장법 및 공시 규정 준수
- 면책 문구(forward-looking statement disclaimer) 포함
- 한국 기관투자자 관점에서의 가독성
"""


def narrative_generator_agent(state: IRState) -> IRState:
    """
    2단계: Gap 기반 IR 나레이티브 & Q&A 생성
    HIL 반려 시에도 이 노드로 돌아와 재생성
    """
    company_name = state["company_name"]
    company_code = state["company_code"]
    gaps = state.get("strategy_gaps", [])
    iteration = state.get("iteration_count", 0)
    rejection_reason = state.get("rejection_reason", "")

    record_action(state, "narrative_generator_agent", "start", {
        "iteration": iteration,
        "rejection_reason": rejection_reason,
    })

    # 공시/뉴스 요약
    filings = state.get("dart_filings", [])
    news = state.get("news_items", [])
    market_signals = state.get("market_signals", [])
    sentiment_info = ""
    if market_signals:
        s = market_signals[-1].get("sentiment_summary", {})
        sentiment_info = f"최근 뉴스 sentiment: {s.get('label','neutral')} (점수: {s.get('avg_score',0)})"

    filing_text = "\n".join(
        f"- [{f.get('rcept_dt','')}] {f.get('report_nm','')}" for f in filings[:8]
    )
    gap_text = "\n".join(f"- {g}" for g in gaps)
    rejection_context = f"\n\n## 이전 반려 사유\n{rejection_reason}" if rejection_reason else ""

    # ── 메인 나레이티브 생성 ────────────────────────────────
    narrative_prompt = f"""## 기업: {company_name} ({company_code})
## 현재 반복: {iteration + 1}회차{rejection_context}

## 최근 공시
{filing_text or "공시 데이터 없음"}

## {sentiment_info}

## 탐지된 IR 커뮤니케이션 Gap
{gap_text or "Gap 없음"}

## 요청
위 Gap을 해소하는 종합 IR 나레이티브(한국어, Markdown 형식)를 작성하세요.

구조:
### 1. 경영 하이라이트
### 2. 전략 방향성 및 중장기 로드맵
### 3. 재무 성과 및 전망
### 4. 리스크 요인 및 대응 전략
### 5. 주주 가치 제고 계획
### 6. Forward-Looking Statement Disclaimer

각 섹션은 투자자가 바로 이해할 수 있도록 구체적이고 데이터 기반으로 작성하세요.
면책 문구(미래 예측, 투자 판단, 리스크)를 반드시 포함하세요."""

    narrative_draft = ""
    try:
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            system=NARRATIVE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": narrative_prompt}],
        )
        narrative_draft = response.content[0].text
    except Exception as e:
        narrative_draft = _fallback_narrative(company_name, gaps)
        record_action(state, "narrative_generator_agent", "llm_fallback", {"error": str(e)})

    # ── Q&A 생성 ──────────────────────────────────────────
    qa_pairs = _generate_qa(company_name, gaps, narrative_draft)

    # ── 브리핑팩 메타데이터 ────────────────────────────────
    briefing_pack = {
        "company_name": company_name,
        "company_code": company_code,
        "created_at": datetime.now().isoformat(),
        "iteration": iteration + 1,
        "sections": ["경영 하이라이트", "전략 방향성", "재무 성과", "리스크 대응", "주주 가치", "면책 문구"],
        "gap_count": len(gaps),
        "narrative_length": len(narrative_draft),
        "qa_count": len(qa_pairs),
    }

    record_action(state, "narrative_generator_agent", "complete", {
        "narrative_length": len(narrative_draft),
        "qa_count": len(qa_pairs),
    })

    return {
        **state,
        "narrative_draft": narrative_draft,
        "qa_pairs": qa_pairs,
        "briefing_pack": briefing_pack,
        "human_approval": None,
        "rejection_reason": None,
        "iteration_count": iteration + 1,
        "current_step": "narrative_generated",
    }


def _generate_qa(company_name: str, gaps: list[str], narrative: str) -> list[dict]:
    """예상 투자자 Q&A 생성"""
    qa_prompt = f"""기업: {company_name}

아래 IR 나레이티브를 읽은 기관투자자가 NDR/IR 미팅에서 할 수 있는 예상 질문 10개와 모범 답변을 생성하세요.
갭 이슈 중심으로: {', '.join(gaps[:5]) if gaps else '일반적 IR 질문'}

나레이티브 요약: {narrative[:1000]}

JSON 배열 형식으로만 응답:
[{{"question": "...", "answer": "..."}}, ...]"""
    try:
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": qa_prompt}],
        )
        text = response.content[0].text
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return _fallback_qa(company_name)


def _fallback_narrative(company_name: str, gaps: list[str]) -> str:
    return f"""# {company_name} IR 나레이티브

### 1. 경영 하이라이트
{company_name}은(는) 지속적인 성장을 통해 주주 가치를 극대화하고 있습니다.

### 2. 전략 방향성 및 중장기 로드맵
- 핵심 사업 경쟁력 강화
- 신성장 동력 발굴 및 투자 확대
- 글로벌 시장 점유율 확대

### 3. 재무 성과 및 전망
안정적인 매출 성장과 수익성 개선을 지속하고 있습니다.

### 4. 리스크 요인 및 대응 전략
거시경제 불확실성에 대한 선제적 리스크 관리를 진행 중입니다.

### 5. 주주 가치 제고 계획
배당 안정성 유지 및 자사주 매입을 통해 주주 가치를 제고합니다.

### 6. Forward-Looking Statement Disclaimer
본 자료에 포함된 미래 예측 정보는 현재의 가정과 기대에 기반하며, 실제 결과는 다를 수 있습니다.
투자 판단은 투자자 본인의 책임이며, 리스크 요인을 충분히 검토하시기 바랍니다.
"""


def _fallback_qa(company_name: str) -> list[dict]:
    return [
        {"question": "올해 연간 실적 가이던스는 어떻게 됩니까?", "answer": "당사는 안정적인 매출 성장과 수익성 개선을 목표로 하고 있으며, 구체적인 수치는 분기 실적 발표 시 공유드리겠습니다."},
        {"question": "주요 리스크 요인은 무엇입니까?", "answer": "거시경제 불확실성, 원자재 가격 변동, 경쟁 심화 등을 주요 리스크로 관리하고 있습니다."},
        {"question": "배당 정책 변경 계획이 있습니까?", "answer": "안정적인 배당을 유지하는 것이 원칙이며, 이익 증가에 따른 점진적 배당 확대를 검토 중입니다."},
        {"question": "해외 시장 전략은 어떻게 됩니까?", "answer": "핵심 글로벌 시장에서의 점유율 확대를 위해 현지화 전략과 파트너십을 강화하고 있습니다."},
        {"question": "ESG 추진 현황을 설명해 주십시오.", "answer": "탄소중립 로드맵, 공급망 ESG 관리, 이사회 다양성 강화 등 종합적인 ESG 전략을 이행 중입니다."},
    ]
