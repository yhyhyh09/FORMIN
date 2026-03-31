"""
브리핑팩 생성 & 다운로드 컴포넌트
"""
from __future__ import annotations
import io
from datetime import datetime
import streamlit as st
from utils.helpers import now_str


def render_briefing_tab(state: dict) -> None:
    """탭 2: 나레이티브 & 브리핑팩"""
    st.header("📦 IR 나레이티브 & 브리핑팩")

    narrative = state.get("narrative_draft", "")
    qa_pairs = state.get("qa_pairs", [])
    briefing_pack = state.get("briefing_pack", {})
    company_name = state.get("company_name", "기업")

    if not narrative:
        st.info("나레이티브가 아직 생성되지 않았습니다. 워크플로우를 실행하세요.")
        return

    # ── 브리핑팩 메타데이터 ────────────────────────────────
    if briefing_pack:
        col1, col2, col3 = st.columns(3)
        col1.metric("생성 시각", briefing_pack.get("created_at", "")[:16])
        col2.metric("재생성 횟수", f"{briefing_pack.get('iteration', 1)}회")
        col3.metric("Q&A 개수", f"{briefing_pack.get('qa_count', 0)}쌍")

    st.divider()

    # ── 나레이티브 표시 ────────────────────────────────────
    st.subheader("📝 IR 나레이티브")
    st.markdown(narrative)

    # ── 다운로드 버튼 ─────────────────────────────────────
    col_md, col_pdf = st.columns(2)

    with col_md:
        md_content = _build_markdown_briefing(company_name, narrative, qa_pairs)
        st.download_button(
            label="⬇️ Markdown 다운로드",
            data=md_content.encode("utf-8"),
            file_name=f"{company_name}_IR_브리핑팩_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
        )

    with col_pdf:
        pdf_bytes = _build_pdf_briefing(company_name, narrative, qa_pairs)
        if pdf_bytes:
            st.download_button(
                label="⬇️ PDF 다운로드",
                data=pdf_bytes,
                file_name=f"{company_name}_IR_브리핑팩_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )
        else:
            st.caption("PDF 생성에는 reportlab 패키지가 필요합니다.")

    st.divider()

    # ── Q&A ──────────────────────────────────────────────
    st.subheader("❓ 예상 투자자 Q&A")
    if qa_pairs:
        for i, qa in enumerate(qa_pairs, 1):
            with st.expander(f"Q{i}. {qa.get('question', '')}"):
                st.write(f"**A:** {qa.get('answer', '')}")
    else:
        st.info("Q&A 데이터 없음")


def _build_markdown_briefing(company_name: str, narrative: str, qa_pairs: list[dict]) -> str:
    """Markdown 브리핑팩 생성"""
    qa_text = ""
    for i, qa in enumerate(qa_pairs, 1):
        qa_text += f"\n**Q{i}. {qa.get('question', '')}**\n\n{qa.get('answer', '')}\n"

    return f"""# {company_name} IR 브리핑팩

> 생성일시: {now_str()}
> 이 문서는 AI가 생성한 초안입니다. 배포 전 IR 담당자의 검토가 필요합니다.

---

{narrative}

---

## 예상 Q&A

{qa_text}
"""


def _build_pdf_briefing(
    company_name: str, narrative: str, qa_pairs: list[dict]
) -> bytes | None:
    """PDF 브리핑팩 생성 (reportlab)"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        story = []

        # 제목
        story.append(Paragraph(f"{company_name} IR 브리핑팩", styles["Title"]))
        story.append(Paragraph(f"생성: {now_str()}", styles["Normal"]))
        story.append(Spacer(1, 10*mm))

        # 나레이티브 (Markdown 태그 단순 제거)
        import re
        clean = re.sub(r'#+\s*', '', narrative)
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
        for line in clean.split('\n'):
            if line.strip():
                story.append(Paragraph(line.strip(), styles["Normal"]))
                story.append(Spacer(1, 3*mm))

        # Q&A
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph("예상 Q&A", styles["Heading1"]))
        for i, qa in enumerate(qa_pairs, 1):
            story.append(Paragraph(f"Q{i}. {qa.get('question', '')}", styles["Heading2"]))
            story.append(Paragraph(qa.get("answer", ""), styles["Normal"]))
            story.append(Spacer(1, 5*mm))

        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None
