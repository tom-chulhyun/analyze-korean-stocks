"""DART 공시 데이터 수집기"""

from datetime import date

import OpenDartReader

from stock_analyzer.config import get_settings
from stock_analyzer.models import FinancialData


class DartCollector:
    """DART 재무제표 수집기"""

    def __init__(self) -> None:
        settings = get_settings()
        self._dart: OpenDartReader | None = None
        if settings.dart_api_key:
            self._dart = OpenDartReader(settings.dart_api_key)

    @property
    def is_available(self) -> bool:
        """DART API 사용 가능 여부"""
        return self._dart is not None

    def get_corp_code(self, stock_code: str) -> str | None:
        """종목코드 → DART 기업코드 변환"""
        if not self._dart:
            return None

        try:
            # OpenDartReader는 종목코드로 직접 조회 가능
            corp_code = self._dart.find_corp_code(stock_code)
            return corp_code
        except Exception:
            return None

    def get_financial_statements(
        self,
        stock_code: str,
        years: list[int] | None = None,
    ) -> list[FinancialData]:
        """재무제표 조회 (복수 연도)"""
        if not self._dart:
            return []

        if years is None:
            current_year = date.today().year
            years = [current_year, current_year - 1]

        financials = []

        for year in years:
            try:
                # 연간 재무제표 조회 (사업보고서)
                fs = self._dart.finstate(stock_code, year, reprt_code="11011")

                if fs is None or fs.empty:
                    # 분기보고서로 재시도
                    fs = self._dart.finstate(stock_code, year)

                if fs is not None and not fs.empty:
                    financial = self._parse_financial_statement(fs, year)
                    if financial:
                        financials.append(financial)

            except Exception:
                continue

        return financials

    def get_company_overview(self, stock_code: str) -> dict | None:
        """기업 개황 정보"""
        if not self._dart:
            return None

        try:
            overview = self._dart.company(stock_code)
            if overview is not None:
                return {
                    "corp_name": overview.get("corp_name", ""),
                    "corp_name_eng": overview.get("corp_name_eng", ""),
                    "ceo_nm": overview.get("ceo_nm", ""),
                    "corp_cls": overview.get("corp_cls", ""),
                    "est_dt": overview.get("est_dt", ""),
                    "adres": overview.get("adres", ""),
                    "hm_url": overview.get("hm_url", ""),
                    "ir_url": overview.get("ir_url", ""),
                    "induty_code": overview.get("induty_code", ""),
                }
        except Exception:
            pass

        return None

    def _parse_financial_statement(
        self,
        fs: "pd.DataFrame",
        year: int,
    ) -> FinancialData | None:
        """재무제표 DataFrame을 FinancialData로 변환"""
        try:
            # 연결재무제표 우선, 없으면 개별재무제표
            fs_type = fs[fs["fs_div"] == "CFS"]  # 연결
            if fs_type.empty:
                fs_type = fs[fs["fs_div"] == "OFS"]  # 개별

            if fs_type.empty:
                fs_type = fs

            # 당기 데이터 추출
            def get_value(account_nm: str) -> float | None:
                row = fs_type[fs_type["account_nm"].str.contains(account_nm, na=False)]
                if not row.empty:
                    val = row.iloc[0].get("thstrm_amount")
                    if val and str(val) not in ["-", "", "nan"]:
                        try:
                            return float(str(val).replace(",", ""))
                        except ValueError:
                            return None
                return None

            revenue = get_value("매출액") or get_value("영업수익")
            operating_income = get_value("영업이익")
            net_income = get_value("당기순이익") or get_value("분기순이익")

            return FinancialData(
                year=year,
                quarter="Annual",
                revenue=revenue,
                operating_income=operating_income,
                net_income=net_income,
                per=None,  # DART에서 직접 제공하지 않음
                pbr=None,
                roe=None,
            )

        except Exception:
            return None

    def get_recent_disclosures(
        self,
        stock_code: str,
        count: int = 5,
    ) -> list[dict]:
        """최근 공시 목록"""
        if not self._dart:
            return []

        try:
            disclosures = self._dart.list(stock_code, kind="A")  # 전체 공시

            if disclosures is None or disclosures.empty:
                return []

            result = []
            for _, row in disclosures.head(count).iterrows():
                result.append(
                    {
                        "rcept_no": row.get("rcept_no", ""),
                        "rcept_dt": row.get("rcept_dt", ""),
                        "report_nm": row.get("report_nm", ""),
                        "flr_nm": row.get("flr_nm", ""),
                    }
                )

            return result

        except Exception:
            return []
