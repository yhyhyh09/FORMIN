"""
OpenDART API 래퍼
공시 목록, 재무제표, 사업보고서 수집 기능 제공
API 문서: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001
"""
from __future__ import annotations
import httpx
from datetime import datetime, timedelta
from typing import Any
from config.settings import DART_API_KEY, DART_BASE_URL, MAX_DART_FILINGS


def _get(endpoint: str, params: dict) -> dict:
    """DART API GET 요청 공통 처리"""
    params["crtfc_key"] = DART_API_KEY
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{DART_BASE_URL}/{endpoint}", params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") not in ("000", "013"):  # 013 = 데이터 없음
        raise RuntimeError(f"DART API 오류 [{data.get('status')}]: {data.get('message')}")
    return data


def get_recent_filings(corp_code: str, days: int = 90) -> list[dict]:
    """
    최근 N일간 공시 목록 조회
    corp_code: DART 고유번호 (8자리). 종목코드가 아님 — convert_to_corp_code() 사용
    """
    bgn_dt = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    end_dt = datetime.now().strftime("%Y%m%d")
    data = _get("list.json", {
        "corp_code": corp_code,
        "bgn_de": bgn_dt,
        "end_de": end_dt,
        "pblntf_ty": "A",   # 정기공시
        "page_count": MAX_DART_FILINGS,
    })
    items = data.get("list", [])
    return [
        {
            "rcept_no": item.get("rcept_no"),
            "corp_name": item.get("corp_name"),
            "report_nm": item.get("report_nm"),
            "rcept_dt": item.get("rcept_dt"),
            "flr_nm": item.get("flr_nm"),
            "rm": item.get("rm", ""),
        }
        for item in items
    ]


def get_all_filings(corp_code: str, days: int = 30) -> list[dict]:
    """정기/수시 공시 전체 목록 (최근 N일)"""
    bgn_dt = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    end_dt = datetime.now().strftime("%Y%m%d")
    data = _get("list.json", {
        "corp_code": corp_code,
        "bgn_de": bgn_dt,
        "end_de": end_dt,
        "page_count": MAX_DART_FILINGS,
    })
    return data.get("list", [])


def get_financial_statements(corp_code: str, year: int | None = None) -> dict[str, Any]:
    """단일 재무제표 (연간) 조회"""
    if year is None:
        year = datetime.now().year - 1
    data = _get("fnlttSinglAcntAll.json", {
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": "11011",   # 사업보고서
        "fs_div": "OFS",          # 별도재무제표
    })
    items = data.get("list", [])
    result: dict[str, Any] = {"year": year, "items": []}
    for item in items:
        result["items"].append({
            "account_nm": item.get("account_nm"),
            "thstrm_amount": item.get("thstrm_amount"),
            "frmtrm_amount": item.get("frmtrm_amount"),
            "bfefrmtrm_amount": item.get("bfefrmtrm_amount"),
        })
    return result


def search_corp_code(company_name: str) -> str | None:
    """기업명으로 DART 고유번호(corp_code) 검색"""
    import zipfile, io, xml.etree.ElementTree as ET
    url = f"{DART_BASE_URL}/corpCode.xml"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params={"crtfc_key": DART_API_KEY})
        resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        with z.open("CORPCODE.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    for item in root.iter("list"):
        name = item.findtext("corp_name", "")
        if company_name in name:
            return item.findtext("corp_code")
    return None


def get_large_shareholder_changes(corp_code: str, days: int = 90) -> list[dict]:
    """대량보유 변동 공시 수집 (5% 룰)"""
    bgn_dt = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    end_dt = datetime.now().strftime("%Y%m%d")
    data = _get("list.json", {
        "corp_code": corp_code,
        "bgn_de": bgn_dt,
        "end_de": end_dt,
        "pblntf_ty": "B",   # 주요사항보고
        "page_count": 20,
    })
    filings = data.get("list", [])
    return [f for f in filings if "대량보유" in f.get("report_nm", "")]


def get_major_holder_report(corp_code: str) -> list[dict]:
    """최대주주 현황 조회"""
    data = _get("hyslrSttus.json", {
        "corp_code": corp_code,
        "bsns_year": str(datetime.now().year - 1),
        "reprt_code": "11011",
    })
    return data.get("list", [])
