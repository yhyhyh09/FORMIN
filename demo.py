"""
데모 실행 스크립트 — API 키 없이 샘플 데이터로 전체 흐름 시뮬레이션
"""
import sys, time

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def step(msg):
    print(f"\n  ▶ {msg}")
    time.sleep(0.4)

def ok(msg):
    print(f"    ✓ {msg}")
    time.sleep(0.2)

def warn(msg):
    print(f"    ⚠ {msg}")

def info(msg):
    print(f"    • {msg}")


company_name = "삼성전자"
company_code = "005930"

print()
print("┌─────────────────────────────────────────────────────┐")
print("│   Proactive Strategy & Investor Intelligence Loop   │")
print("│             IR 멀티 에이전트 시스템 데모             │")
print("└─────────────────────────────────────────────────────┘")
print(f"\n  대상 기업: {company_name} ({company_code})")
input("\n  Enter를 누르면 시작합니다...")

# ──────────────────────────────────────────────────────────
section("STEP 1 / 6 │ Supervisor Agent — 워크플로우 초기화")
step("상태 초기화 및 입력값 검증")
ok(f"기업코드: {company_code}")
ok(f"기업명: {company_name}")
ok("LangGraph StateGraph 실행 준비 완료")

# ──────────────────────────────────────────────────────────
section("STEP 2 / 6 │ Monitoring & Intelligence Agent")
step("OpenDART API → 최근 공시 수집")
filings = [
    ("20241115", "분기보고서 (2024.09)"),
    ("20241102", "주요사항보고서(자기주식취득결정)"),
    ("20241028", "기업설명회(IR) 개최 결과"),
    ("20240930", "반기보고서 (2024.06)"),
]
for date, name in filings:
    ok(f"[{date}] {name}")

step("네이버 증권 뉴스 크롤링 + Sentiment 분석")
news = [
    ("positive", +0.7, "삼성전자, 3분기 영업이익 9.1조... 반도체 회복세 뚜렷"),
    ("negative", -0.5, "삼성전자 파운드리 점유율 TSMC에 밀려 축소 우려"),
    ("positive", +0.4, "삼성전자, HBM4 개발 완료... 엔비디아 공급 협상 중"),
    ("neutral",  +0.1, "삼성전자 내년 설비투자 소폭 확대 예정"),
    ("negative", -0.3, "삼성전자 갤럭시 판매량 전년比 감소"),
]
for label, score, title in news:
    emoji = "🟢" if label=="positive" else "🔴" if label=="negative" else "🟡"
    print(f"    {emoji} [{score:+.1f}] {title}")

step("LLM Gap 분석 실행 (Gemini 1.5 Flash)")
gaps = [
    "HBM/AI 반도체 로드맵 투자자 전달 부족 — 경쟁사(SK하이닉스) 대비 메시지 열세",
    "파운드리 점유율 하락에 대한 공식 대응 내러티브 부재",
    "주주환원 정책(자사주 취득) 규모·타이밍 설명 미흡",
    "2025년 설비투자 가이던스 불명확 — 기관투자자 불확실성 증가",
    "ESG·탄소중립 로드맵 IR 자료 반영 미흡",
]
print()
for i, gap in enumerate(gaps, 1):
    warn(f"Gap {i}: {gap}")

# ──────────────────────────────────────────────────────────
section("STEP 3 / 6 │ Narrative Generator Agent")
step("Gap 기반 IR 나레이티브 초안 생성 (Gemini 1.5 Flash)")
time.sleep(0.8)

narrative = """
### 1. 경영 하이라이트
삼성전자는 2024년 3분기 영업이익 9.1조원을 달성하며 반도체 업황 회복을
선도하고 있습니다. HBM3E 양산 및 HBM4 개발 완료로 AI 인프라 핵심 공급자
위상을 강화하고 있으며, 엔비디아·AMD 등 글로벌 AI 기업과의 협력을 확대
중입니다.

### 2. 전략 방향성
① AI 메모리(HBM) 생산능력 2025년까지 3배 확대
② 파운드리: 2나노 GAA 공정 2025 H1 양산 — 고부가 고객사 집중 전략
③ 스마트폰: Galaxy AI 기능 확대로 ASP 향상 및 교체 수요 창출

### 3. 주주환원
2024년 자사주 3조원 취득 완료. 분기 배당 유지. 2025년 추가 환원 검토 중.

### 4. Forward-Looking Statement Disclaimer
본 자료의 미래 예측 정보는 현재 가정에 기반하며 실제 결과는 다를 수 있습니다.
투자 판단은 투자자 본인의 책임이며 제반 리스크를 충분히 검토하시기 바랍니다.
"""
print(narrative)
ok("나레이티브 생성 완료 (1,240자)")

step("예상 투자자 Q&A 10쌍 생성")
qa = [
    ("HBM 경쟁력이 SK하이닉스 대비 어떻게 다른가요?",
     "HBM4 독자 설계로 전력효율 15% 개선, 2025 Q2 엔비디아 공급 예정입니다."),
    ("파운드리 점유율 하락 대응 전략은?",
     "고부가 AI칩·자동차 반도체 집중으로 마진 중심 전략으로 전환 중입니다."),
    ("2025년 설비투자 계획은?",
     "HBM·파운드리 중심으로 전년 대비 10~15% 증가를 검토 중입니다."),
]
for i, (q, a) in enumerate(qa, 1):
    print(f"\n    Q{i}. {q}")
    print(f"    A.  {a}")
print(f"\n    ... 외 7쌍 추가 생성")

# ──────────────────────────────────────────────────────────
section("STEP 4 / 6 │ Profile & Targeting Agent")
step("DART 대량보유 공시 기반 투자자 프로파일 구축")
step("13F 스타일 Fit 점수 계산")
investors = [
    ("국민연금공단",       "pension_fund",    8.2, +0.3, 0.82),
    ("블랙록",            "foreign_passive", 5.1, -0.2, 0.71),
    ("미래에셋자산운용",   "asset_manager",   3.4, +1.1, 0.89),
    ("피델리티인터내셔널", "foreign_active",  2.7, +0.8, 0.85),
    ("싱가포르투자청(GIC)","sovereign_wealth",1.9,  0.0, 0.68),
]
print(f"\n    {'기관명':<22} {'유형':<18} {'보유%':>5} {'변동%':>6} {'Fit':>5}")
print(f"    {'-'*58}")
for name, itype, hold, chg, fit in investors:
    bar = "█" * int(fit * 10)
    print(f"    {name:<22} {itype:<18} {hold:>5.1f} {chg:>+6.1f} {fit:>5.2f} {bar}")

# ──────────────────────────────────────────────────────────
section("STEP 5 / 6 │ Personalization & Engagement Agent")
step("타깃 투자자별 맞춤 메시지 생성")
print("""
  ─── 미래에셋자산운용 (Fit: 0.89) ──────────────────────
  [이메일]
  미래에셋자산운용 귀중,
  당사의 HBM4 양산 본격화 및 2025년 주주환원 계획을
  공유드리고자 NDR 미팅을 요청드립니다.

  [어젠다 — 30분]
  • AI 반도체 성장 모멘텀 및 HBM 로드맵 (10분)
  • 밸류에이션 및 2025 가이던스 (10분)
  • Q&A (10분)

  [핵심 메시지]
  ① HBM4 엔비디아 공급 → 2025 ASP 30% 상승 예상
  ② 파운드리 구조조정 → 마진 개선 가시화
  ③ 자사주 추가 취득 검토 → 주주환원 강화

  ─── 피델리티인터내셔널 (Fit: 0.85) ────────────────────
  [핵심 메시지]
  ① 경영진 교체 후 전략 일관성 유지 확인
  ② 경쟁우위: 수직계열화(설계~제조~패키징) 유일 보유
  ③ 3년 EPS CAGR 25% 전망""")

# ──────────────────────────────────────────────────────────
section("STEP 6 / 6 │ Optimization & Compliance Agent")
step("공시 규정 준수 검사 (자본시장법, 선별공시 규정)")
ok("선별공시 위반 표현: 없음")
ok("투자 과대포장 표현: 없음")
ok("면책 문구 포함 확인")
warn("타이밍 주의: 실적 발표 시즌 — 미확정 수치 표현 주의")

step("KPI 계산")
kpis = {
    "Gap 해소율": "100% (5/5)",
    "타깃 투자자": "10명",
    "평균 Fit 점수": "0.79",
    "개인화 메시지": "5건",
    "Q&A 쌍": "10쌍",
    "컴플라이언스": "통과 (경고 1건)",
}
for k, v in kpis.items():
    ok(f"{k}: {v}")

step("Audit Trail 저장 → audit_logs/삼성전자_20241115.json")

# ──────────────────────────────────────────────────────────
section("⏸  Human-in-the-Loop 승인 게이트")
print("""
  Streamlit 대시보드에서 IR 담당자가 검토 후 결정:

  ┌──────────────────────────────────────────────────┐
  │  나레이티브가 생성되었습니다. 검토 후 선택하세요.  │
  │                                                  │
  │    [✅ 승인 → 브리핑팩 확정 & PDF 다운로드]       │
  │    [❌ 반려 → 사유 입력 후 자동 재생성]           │
  └──────────────────────────────────────────────────┘
""")

choice = input("  데모에서 선택: 승인(y) / 반려(n)? ").strip().lower()

if choice == "n":
    reason = input("  반려 사유: ").strip() or "HBM 경쟁력 섹션 보강 필요"
    print(f"\n  반려 처리 → 재생성 시작 (사유: {reason})")
    time.sleep(0.6)
    print("  ▶ Narrative Generator Agent 재실행...")
    time.sleep(0.8)
    ok("나레이티브 2차 생성 완료 — 반려 사유 반영")
    print("  ▶ Optimization & Compliance Agent 재실행...")
    time.sleep(0.5)
    ok("컴플라이언스 재검사 통과")
    print("\n  → 다시 승인 게이트로 이동 (Streamlit에서 재검토)")
else:
    print()
    ok("승인 완료 → 브리핑팩 확정")
    ok("PDF 다운로드 준비 완료: 삼성전자_IR_브리핑팩_20241115.pdf")
    ok("Audit Trail 영구 저장 완료")
    ok("Feedback Loop 종료 → 워크플로우 완료")

# ──────────────────────────────────────────────────────────
section("완료 요약")
print(f"""
  기업:           {company_name} ({company_code})
  탐지된 Gap:     5개
  생성된 나레이티브: 약 1,240자
  예상 Q&A:       10쌍
  타깃 투자자:     10명 (Fit 점수 기반)
  개인화 메시지:   5건
  컴플라이언스:    통과

  실제 실행 시 추가 기능:
  • Streamlit 대시보드 (브라우저 UI)
  • PDF 브리핑팩 다운로드
  • 실시간 DART 공시 & 네이버 뉴스 수집
  • 자연어 질의 (예: "국민연금에게 뭘 강조하지?")
""")
