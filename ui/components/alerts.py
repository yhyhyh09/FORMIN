"""
Gap 알림 & 모니터링 현황 컴포넌트
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from utils.helpers import sentiment_to_emoji, format_date


def render_alerts_tab(state: dict) -> None:
    """탭 1: Gap 알림 & 모니터링 현황"""
    st.header("📡 모니터링 현황 & Gap 알림")

    # ── 요약 메트릭 ───────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    dart_count = len(state.get("dart_filings", []))
    news_count = len(state.get("news_items", []))
    gap_count = len(state.get("strategy_gaps", []))
    signals = state.get("market_signals", [])
    sentiment_label = "N/A"
    avg_score = 0.0
    if signals:
        s = signals[-1].get("sentiment_summary", {})
        sentiment_label = s.get("label", "neutral")
        avg_score = s.get("avg_score", 0.0)

    col1.metric("📄 수집 공시", f"{dart_count}건")
    col2.metric("📰 수집 뉴스", f"{news_count}건")
    col3.metric("⚠️ 탐지 Gap", f"{gap_count}개")
    col4.metric(
        f"Sentiment {sentiment_to_emoji(sentiment_label)}",
        sentiment_label,
        delta=f"{avg_score:+.2f}",
    )

    st.divider()

    # ── 전략 Gap 알림 ─────────────────────────────────────
    st.subheader("⚠️ 전략 커뮤니케이션 Gap")
    gaps = state.get("strategy_gaps", [])
    if gaps:
        for i, gap in enumerate(gaps, 1):
            st.warning(f"**Gap {i}:** {gap}")
    else:
        st.success("탐지된 Gap 없음")

    st.divider()

    # ── DART 공시 목록 ────────────────────────────────────
    st.subheader("📋 최근 DART 공시")
    filings = state.get("dart_filings", [])
    if filings:
        df = pd.DataFrame([
            {
                "공시일": format_date(f.get("rcept_dt", "")),
                "보고서명": f.get("report_nm", ""),
                "제출인": f.get("flr_nm", ""),
                "비고": f.get("rm", ""),
            }
            for f in filings
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("공시 데이터 없음")

    st.divider()

    # ── 뉴스 Sentiment ────────────────────────────────────
    st.subheader("📰 최근 뉴스 & Sentiment")
    news = state.get("news_items", [])
    if news:
        for item in news[:10]:
            label = item.get("sentiment_label", "neutral")
            score = item.get("sentiment_score", 0.0)
            emoji = sentiment_to_emoji(label)
            title = item.get("title", "")
            date = item.get("date", "")
            url = item.get("url", "")

            with st.expander(f"{emoji} {title[:60]}... | {score:+.2f}"):
                st.write(item.get("description", ""))
                if date:
                    st.caption(f"날짜: {date}")
                if url:
                    st.caption(f"URL: {url}")
    else:
        st.info("뉴스 데이터 없음")
