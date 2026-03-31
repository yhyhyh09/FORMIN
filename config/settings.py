"""
설정 모듈: 환경변수 로드 및 전역 상수 정의
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 기준으로 .env 로드
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# ── API Keys ──────────────────────────────────────────────
DART_API_KEY: str = os.getenv("DART_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# ── 기본 기업 정보 ────────────────────────────────────────
DEFAULT_COMPANY_CODE: str = os.getenv("DEFAULT_COMPANY_CODE", "005930")
DEFAULT_COMPANY_NAME: str = os.getenv("DEFAULT_COMPANY_NAME", "삼성전자")

# ── 경로 설정 ─────────────────────────────────────────────
CHECKPOINT_DIR: Path = Path(os.getenv("CHECKPOINT_DIR", str(BASE_DIR / "checkpoints")))
AUDIT_LOG_DIR: Path = Path(os.getenv("AUDIT_LOG_DIR", str(BASE_DIR / "audit_logs")))
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM 설정 ─────────────────────────────────────────────
LLM_MODEL: str = "claude-sonnet-4-6"
LLM_MAX_TOKENS: int = 4096
LLM_TEMPERATURE: float = 0.3

# ── OpenDART API ──────────────────────────────────────────
DART_BASE_URL: str = "https://opendart.fss.or.kr/api"

# ── 모니터링 설정 ─────────────────────────────────────────
MAX_DART_FILINGS: int = 20       # 최근 공시 수집 개수
MAX_NEWS_ITEMS: int = 30         # 최근 뉴스 수집 개수
SENTIMENT_THRESHOLD_NEG: float = -0.3   # 부정 sentiment 임계값
SENTIMENT_THRESHOLD_POS: float = 0.3    # 긍정 sentiment 임계값
MAX_ITERATIONS: int = 3          # HIL 반려 시 최대 재생성 횟수

# ── 투자자 타깃팅 ─────────────────────────────────────────
MAX_TARGETED_INVESTORS: int = 10
INVESTOR_SCORE_THRESHOLD: float = 0.6   # 타깃팅 최소 점수

# ── Streamlit ─────────────────────────────────────────────
STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))


def validate_keys() -> dict[str, bool]:
    """API 키 설정 여부 반환"""
    return {
        "DART_API_KEY": bool(DART_API_KEY),
        "ANTHROPIC_API_KEY": bool(ANTHROPIC_API_KEY),
        "TAVILY_API_KEY": bool(TAVILY_API_KEY),
    }
