"""
웹 검색 툴
Tavily API가 설정된 경우 우선 사용, 없으면 DuckDuckGo fallback
"""
from __future__ import annotations
from config.settings import TAVILY_API_KEY, MAX_NEWS_ITEMS


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    웹 검색 수행. 결과: [{title, url, content, score}]
    """
    if TAVILY_API_KEY:
        return _tavily_search(query, max_results)
    return _duckduckgo_search(query, max_results)


def _tavily_search(query: str, max_results: int) -> list[dict]:
    """Tavily API 검색"""
    import httpx
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "include_raw_content": False,
        },
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:500],
            "score": r.get("score", 0.0),
        }
        for r in results
    ]


def _duckduckgo_search(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo 검색 (API 키 불필요)"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, region="kr-kr"))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "content": r.get("body", "")[:500],
                "score": 1.0,
            }
            for r in results
        ]
    except Exception as e:
        return [{"title": "검색 오류", "url": "", "content": str(e), "score": 0.0}]


def search_company_news(company_name: str, days: int = 7) -> list[dict]:
    """기업명 기반 최근 뉴스 검색"""
    queries = [
        f"{company_name} 실적 전망 {days}일",
        f"{company_name} 경영 전략 IR",
        f"{company_name} 투자자 기관",
    ]
    results: list[dict] = []
    for q in queries:
        results.extend(search_web(q, max_results=5))
    # 중복 URL 제거
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique[:MAX_NEWS_ITEMS]


def search_competitor_news(company_name: str, industry: str = "") -> list[dict]:
    """경쟁사 동향 검색"""
    query = f"{industry} 경쟁사 실적 전략 최근" if industry else f"{company_name} 경쟁사 업계 동향"
    return search_web(query, max_results=8)
