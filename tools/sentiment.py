"""
감성 분석 모듈
네이버 증권 뉴스 크롤링 + 규칙 기반 한국어 sentiment 분석
(KoBERT 없이도 동작하는 경량 구현)
"""
from __future__ import annotations
import re
import httpx
from bs4 import BeautifulSoup
from config.settings import MAX_NEWS_ITEMS

# 한국어 금융 감성 사전 (확장 가능)
_POSITIVE_WORDS = {
    "상승", "급등", "호실적", "매출 증가", "영업이익", "흑자", "성장", "수주",
    "신고가", "강세", "매수", "목표가 상향", "어닝서프라이즈", "턴어라운드",
    "수익성 개선", "배당 확대", "자사주 매입", "계약 체결", "신제품", "확대",
    "긍정", "기대", "호조", "개선", "증가", "달성", "초과", "양호",
}

_NEGATIVE_WORDS = {
    "하락", "급락", "부진", "매출 감소", "영업손실", "적자", "감소", "취소",
    "신저가", "약세", "매도", "목표가 하향", "어닝쇼크", "리콜", "소송",
    "수익성 악화", "배당 축소", "유상증자", "계약 해지", "구조조정", "축소",
    "부정", "우려", "악화", "감소", "미달", "실망", "불확실", "위험",
    "규제", "제재", "조사", "손실", "부채", "위기",
}


def _simple_sentiment_score(text: str) -> float:
    """
    규칙 기반 감성 점수 계산. -1.0 (매우 부정) ~ 1.0 (매우 긍정)
    """
    pos = sum(1 for w in _POSITIVE_WORDS if w in text)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


def _label(score: float) -> str:
    if score >= 0.3:
        return "positive"
    elif score <= -0.3:
        return "negative"
    return "neutral"


def analyze_text_sentiment(text: str) -> dict:
    """단일 텍스트 감성 분석"""
    score = _simple_sentiment_score(text)
    return {
        "score": score,
        "label": _label(score),
        "text_preview": text[:100],
    }


def crawl_naver_finance_news(company_name: str, max_items: int = 20) -> list[dict]:
    """
    네이버 증권 뉴스 크롤링
    실제 운영에서는 requests + BeautifulSoup으로 뉴스 제목/요약 수집
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    results: list[dict] = []
    try:
        # 네이버 뉴스 검색
        url = "https://search.naver.com/search.naver"
        params = {
            "where": "news",
            "query": f"{company_name} 주식 IR",
            "sm": "tab_jum",
            "sort": "1",  # 최신순
        }
        resp = httpx.get(url, params=params, headers=headers, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "lxml")

        # 뉴스 항목 파싱
        news_items = soup.select("div.news_area")[:max_items]
        for item in news_items:
            title_el = item.select_one("a.news_tit")
            desc_el = item.select_one("div.dsc_wrap")
            date_el = item.select_one("span.info")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            desc = desc_el.get_text(strip=True) if desc_el else ""
            date = date_el.get_text(strip=True) if date_el else ""
            url_link = title_el.get("href", "")

            combined_text = f"{title} {desc}"
            sentiment = analyze_text_sentiment(combined_text)

            results.append({
                "title": title,
                "description": desc,
                "url": url_link,
                "date": date,
                "source": "naver_finance",
                "sentiment_score": sentiment["score"],
                "sentiment_label": sentiment["label"],
            })
    except Exception as e:
        results.append({
            "title": "크롤링 오류",
            "description": str(e),
            "url": "",
            "date": "",
            "source": "error",
            "sentiment_score": 0.0,
            "sentiment_label": "neutral",
        })
    return results


def aggregate_sentiment(news_items: list[dict]) -> dict:
    """뉴스 목록 전체 sentiment 집계"""
    if not news_items:
        return {"avg_score": 0.0, "label": "neutral", "pos": 0, "neg": 0, "neu": 0}
    scores = [item.get("sentiment_score", 0.0) for item in news_items]
    avg = sum(scores) / len(scores)
    labels = [item.get("sentiment_label", "neutral") for item in news_items]
    return {
        "avg_score": round(avg, 3),
        "label": _label(avg),
        "pos": labels.count("positive"),
        "neg": labels.count("negative"),
        "neu": labels.count("neutral"),
        "total": len(news_items),
    }
