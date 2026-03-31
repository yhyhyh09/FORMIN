"""
Monitoring & Intelligence Agent
DART 공시 수집, 뉴스/sentiment 모니터링, 경영전략 Gap 탐지
"""
from __future__ import annotations
from datetime import datetime
from utils.llm import chat
from graph.state import IRState
from tools.dart_api import search_corp_code, get_recent_filings, get_all_filings
from tools.sentiment import crawl_naver_finance_news, aggregate_sentiment
from tools.web_search import search_company_news
from utils.audit import record_action


def monitoring_agent(state: IRState) -> IRState:
    """
    1단계: 공시/뉴스 수집 및 Gap 분석
    """
    company_code = state["company_code"]
    company_name = state["company_name"]

    record_action(state, "monitoring_agent", "start", {"company": company_name})

    # ── DART 공시 수집 ────────────────────────────────────
    dart_filings: list[dict] = []
    all_filings: list[dict] = []
    try:
        # corp_code 조회 (DART 고유번호)
        corp_code = search_corp_code(company_name)
        if corp_code:
            dart_filings = get_recent_filings(corp_code, days=90)
            all_filings = get_all_filings(corp_code, days=30)
        else:
            # API 키 미설정 또는 기업명 불일치 시 샘플 데이터
            dart_filings = _sample_filings(company_name)
            all_filings = dart_filings
    except Exception as e:
        dart_filings = _sample_filings(company_name)
        all_filings = dart_filings
        record_action(state, "monitoring_agent", "dart_fallback", {"error": str(e)})

    # ── 뉴스 & Sentiment ─────────────────────────────────
    news_items: list[dict] = []
    try:
        naver_news = crawl_naver_finance_news(company_name, max_items=15)
        web_news = search_company_news(company_name, days=7)
        news_items = naver_news + [
            {**n, "sentiment_score": 0.0, "sentiment_label": "neutral", "source": "web"}
            for n in web_news
            if not any(x["url"] == n["url"] for x in naver_news)
        ]
    except Exception as e:
        news_items = _sample_news(company_name)
        record_action(state, "monitoring_agent", "news_fallback", {"error": str(e)})

    sentiment_summary = aggregate_sentiment(news_items)

    # ── LLM Gap 분석 ──────────────────────────────────────
    filing_summary = "\n".join(
        f"- [{f.get('rcept_dt','')}] {f.get('report_nm','')}" for f in dart_filings[:10]
    )
    news_summary = "\n".join(
        f"- [{n.get('sentiment_label','neutral')}] {n.get('title','')}"
        for n in news_items[:15]
    )

    gap_prompt = f"""당신은 한국 상장사 IR 전문가입니다.
아래 {company_name}의 공시 및 뉴스 데이터를 분석하여 경영전략 커뮤니케이션 Gap을 탐지하세요.

## 최근 공시 목록
{filing_summary if filing_summary else "공시 데이터 없음"}

## 최근 뉴스 (sentiment: {sentiment_summary.get('label','neutral')}, 평균점수: {sentiment_summary.get('avg_score', 0)})
{news_summary if news_summary else "뉴스 데이터 없음"}

## 요청
다음 관점에서 IR 커뮤니케이션 Gap을 3~7개 식별하세요:
1. 투자자에게 충분히 전달되지 않은 전략 포인트
2. 부정 sentiment 대응이 필요한 이슈
3. 경쟁사 대비 차별화 포인트 미언급
4. 실적/가이던스 공백
5. ESG/지배구조 커뮤니케이션 부족

JSON 배열 형식으로만 응답: ["Gap1", "Gap2", ...]"""

    strategy_gaps: list[str] = []
    try:
        import json, re
        text = chat(gap_prompt)
        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            strategy_gaps = json.loads(match.group())
    except Exception as e:
        strategy_gaps = [
            f"{company_name} 중장기 성장 전략 투자자 전달 미흡",
            "최근 부정 뉴스 대응 메시지 부재",
            "경쟁사 대비 차별화 포인트 IR 자료 미반영",
        ]
        record_action(state, "monitoring_agent", "gap_analysis_fallback", {"error": str(e)})

    record_action(state, "monitoring_agent", "complete", {
        "filings_count": len(dart_filings),
        "news_count": len(news_items),
        "gaps_found": len(strategy_gaps),
        "sentiment": sentiment_summary.get("label"),
    })

    return {
        **state,
        "dart_filings": dart_filings,
        "news_items": news_items,
        "market_signals": [{"sentiment_summary": sentiment_summary, "timestamp": datetime.now().isoformat()}],
        "strategy_gaps": strategy_gaps,
        "current_step": "monitoring_complete",
    }


def _sample_filings(company_name: str) -> list[dict]:
    """테스트용 샘플 공시 (API 키 없을 때)"""
    today = datetime.now().strftime("%Y%m%d")
    return [
        {"rcept_dt": today, "corp_name": company_name, "report_nm": "분기보고서 (2024.09)", "flr_nm": company_name, "rm": ""},
        {"rcept_dt": today, "corp_name": company_name, "report_nm": "주요사항보고서(자기주식취득결정)", "flr_nm": company_name, "rm": ""},
        {"rcept_dt": today, "corp_name": company_name, "report_nm": "기업설명회(IR) 개최 결과", "flr_nm": company_name, "rm": ""},
        {"rcept_dt": today, "corp_name": company_name, "report_nm": "임원ㆍ주요주주특정증권등소유상황보고서", "flr_nm": "임원A", "rm": ""},
    ]


def _sample_news(company_name: str) -> list[dict]:
    """테스트용 샘플 뉴스"""
    return [
        {"title": f"{company_name}, 3분기 영업이익 시장 예상 상회", "description": "어닝서프라이즈", "url": "", "date": "", "source": "sample", "sentiment_score": 0.6, "sentiment_label": "positive"},
        {"title": f"{company_name} 내년 설비 투자 확대 발표", "description": "신규 라인 증설", "url": "", "date": "", "source": "sample", "sentiment_score": 0.4, "sentiment_label": "positive"},
        {"title": f"{company_name} 글로벌 경쟁 심화 우려", "description": "점유율 하락", "url": "", "date": "", "source": "sample", "sentiment_score": -0.4, "sentiment_label": "negative"},
    ]
