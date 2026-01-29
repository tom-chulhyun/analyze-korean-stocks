"""주가 데이터 수집기 (pykrx + FinanceDataReader)"""

import re
from datetime import date, timedelta

import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pykrx import stock as pykrx

from stock_analyzer.models import PriceData, StockInfo


class StockNotFoundError(Exception):
    """존재하지 않는 종목"""

    pass


class StockPriceCollector:
    """주가 데이터 수집기"""

    def __init__(self) -> None:
        self._ticker_cache: dict[str, str] = {}

    def get_stock_info(self, code: str) -> StockInfo:
        """종목 기본 정보 조회"""
        # 종목명 조회
        name = self._get_stock_name(code)
        if not name:
            raise StockNotFoundError(f"종목코드 {code}를 찾을 수 없습니다.")

        # 시장 구분
        market = self._get_market(code)

        # 섹터 및 재무 지표 조회 (네이버 금융)
        naver_data = self._get_naver_finance_data(code)
        sectors = naver_data.get("sectors", [])
        per = naver_data.get("per")
        eps = naver_data.get("eps")
        pbr = naver_data.get("pbr")
        bps = naver_data.get("bps")
        dividend_yield = naver_data.get("dividend_yield")

        return StockInfo(
            code=code,
            name=name,
            market=market,
            sectors=sectors,
            per=per,
            eps=eps,
            pbr=pbr,
            bps=bps,
            dividend_yield=dividend_yield,
        )

    def get_ohlcv(
        self,
        code: str,
        start: date,
        end: date,
    ) -> list[PriceData]:
        """OHLCV + 거래대금 + 등락률 조회"""
        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")

        # OHLCV 데이터 조회
        df = pykrx.get_market_ohlcv(start_str, end_str, code)

        if df.empty:
            return []

        # 컬럼명 정리 (인덱스: 날짜, 컬럼: 시가, 고가, 저가, 종가, 거래량, 등락률)
        df = df.reset_index()

        # PriceData 리스트로 변환
        price_data = []
        for _, row in df.iterrows():
            # 거래대금 = 종가 * 거래량 (근사치)
            close_price = float(row["종가"])
            volume = int(row["거래량"])
            trading_value = close_price * volume

            price_data.append(
                PriceData(
                    date=row["날짜"].date() if isinstance(row["날짜"], pd.Timestamp) else row["날짜"],
                    open=float(row["시가"]),
                    high=float(row["고가"]),
                    low=float(row["저가"]),
                    close=close_price,
                    volume=volume,
                    trading_value=trading_value,
                    change_rate=float(row["등락률"]),
                )
            )

        return price_data

    def get_fundamental(self, code: str, target_date: date) -> dict[str, float | None]:
        """PER, PBR 등 기본 지표 조회"""
        date_str = target_date.strftime("%Y%m%d")

        # 해당 날짜에 데이터가 없을 수 있으므로 최근 5일 내 조회
        for i in range(5):
            try_date = (target_date - timedelta(days=i)).strftime("%Y%m%d")
            df = pykrx.get_market_fundamental(try_date, market="ALL")

            if not df.empty and code in df.index:
                row = df.loc[code]
                return {
                    "per": float(row.get("PER", 0)) or None,
                    "pbr": float(row.get("PBR", 0)) or None,
                    "eps": float(row.get("EPS", 0)) or None,
                    "bps": float(row.get("BPS", 0)) or None,
                    "div_yield": float(row.get("DIV", 0)) or None,
                }

        return {"per": None, "pbr": None, "eps": None, "bps": None, "div_yield": None}

    def _get_stock_name(self, code: str) -> str | None:
        """종목명 조회"""
        if code in self._ticker_cache:
            return self._ticker_cache[code]

        # 직접 종목명 조회 시도
        try:
            name = pykrx.get_market_ticker_name(code)
            if name:
                self._ticker_cache[code] = name
                return name
        except Exception:
            pass

        # OHLCV 조회로 종목 존재 여부 확인 (fallback)
        try:
            end = date.today()
            start = end - timedelta(days=30)
            df = pykrx.get_market_ohlcv(
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                code,
            )
            if not df.empty:
                # 종목이 존재하면 코드를 이름으로 사용
                self._ticker_cache[code] = code
                return code
        except Exception:
            pass

        return None

    def _get_market(self, code: str) -> str:
        """시장 구분 조회"""
        # OHLCV 조회로 시장 구분 확인
        try:
            end = date.today()
            start = end - timedelta(days=7)
            start_str = start.strftime("%Y%m%d")
            end_str = end.strftime("%Y%m%d")

            # KOSPI 시도
            df = pykrx.get_market_ohlcv(start_str, end_str, code, market="KOSPI")
            if not df.empty:
                return "KOSPI"

            # KOSDAQ 시도
            df = pykrx.get_market_ohlcv(start_str, end_str, code, market="KOSDAQ")
            if not df.empty:
                return "KOSDAQ"
        except Exception:
            pass

        return "KOSPI"  # 기본값

    def _get_naver_finance_data(self, code: str) -> dict:
        """네이버 금융에서 업종 및 재무 지표 조회"""
        result = {
            "sectors": [],
            "per": None,
            "eps": None,
            "pbr": None,
            "bps": None,
            "dividend_yield": None,
        }

        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=5)

            if resp.status_code != 200:
                return result

            soup = BeautifulSoup(resp.text, "html.parser")

            # 업종 정보 파싱
            sectors = []
            # 패턴 1: 업종 링크
            matches = re.findall(r'class="sub_tit"[^>]*>([^<]+)</a>', resp.text)
            if matches:
                sectors.extend([s.strip() for s in matches if s.strip()])

            # 패턴 2: 업종 텍스트
            if not sectors:
                match = re.search(r'업종.*?<a[^>]*>([^<]+)</a>', resp.text, re.DOTALL)
                if match:
                    sector = match.group(1).strip()
                    if sector:
                        sectors.append(sector)

            result["sectors"] = list(dict.fromkeys(sectors))[:5]

            # PER, PBR 테이블 파싱
            per_table = soup.find("table", {"class": "per_table"})
            if per_table:
                for row in per_table.find_all("tr"):
                    text = row.get_text()

                    # PER 추출 (추정PER 제외)
                    if "PER" in text and "추정" not in text:
                        match = re.search(r"(\d+\.?\d*)\s*배", text)
                        if match:
                            result["per"] = float(match.group(1))
                        # EPS 추출
                        eps_match = re.search(r"(\d{1,3}(?:,\d{3})*)\s*원", text)
                        if eps_match:
                            result["eps"] = float(eps_match.group(1).replace(",", ""))

                    # PBR 추출
                    if "PBR" in text:
                        match = re.search(r"(\d+\.?\d*)\s*배", text)
                        if match:
                            result["pbr"] = float(match.group(1))
                        # BPS 추출
                        bps_match = re.search(r"(\d{1,3}(?:,\d{3})*)\s*원", text)
                        if bps_match:
                            result["bps"] = float(bps_match.group(1).replace(",", ""))

            # 배당수익률 파싱
            div_match = re.search(r"배당수익률.*?(\d+\.?\d*)\s*%", resp.text)
            if div_match:
                result["dividend_yield"] = float(div_match.group(1))

        except Exception:
            pass

        return result

    def validate_code(self, code: str) -> bool:
        """종목코드 유효성 검증"""
        if len(code) != 6 or not code.isdigit():
            return False

        # OHLCV 조회로 검증
        try:
            end = date.today()
            start = end - timedelta(days=30)
            df = pykrx.get_market_ohlcv(
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                code,
            )
            return not df.empty
        except Exception:
            return False

    def get_top_stocks_by_trading_value(
        self,
        target_date: date | None = None,
        market: str = "KOSPI",
        top_n: int = 10,
    ) -> list[dict]:
        """거래대금 상위 종목 조회 (FinanceDataReader 사용)

        Args:
            target_date: 조회 날짜 (미사용, FinanceDataReader는 최신 데이터 반환)
            market: 시장 (KOSPI, KOSDAQ, ALL)
            top_n: 상위 N개

        Returns:
            [{"code": "005930", "name": "삼성전자", "trading_value": 1000000000, "change_rate": 2.5}, ...]
        """
        try:
            # FinanceDataReader로 종목 목록 조회 (최신 거래일 기준)
            if market.upper() == "ALL":
                kospi = fdr.StockListing("KOSPI")
                kosdaq = fdr.StockListing("KOSDAQ")
                df = pd.concat([kospi, kosdaq], ignore_index=True)
            elif market.upper() == "KOSDAQ":
                df = fdr.StockListing("KOSDAQ")
            else:  # KOSPI
                df = fdr.StockListing("KOSPI")

            if df.empty:
                print("종목 목록 조회 실패")
                return []

            # Amount(거래대금) 기준 정렬
            df = df.sort_values("Amount", ascending=False)

            # 상위 N개 선택
            results = []
            for _, row in df.head(top_n).iterrows():
                # 등락률 계산 (ChagesRatio가 있으면 사용, 없으면 계산)
                change_rate = float(row.get("ChagesRatio", 0) or 0)

                results.append({
                    "code": str(row["Code"]),
                    "name": str(row["Name"]),
                    "trading_value": int(row.get("Amount", 0) or 0),
                    "close": int(row.get("Close", 0) or 0),
                    "change_rate": change_rate,
                    "volume": int(row.get("Volume", 0) or 0),
                })

            return results

        except Exception as e:
            print(f"거래대금 상위 종목 조회 실패: {e}")
            return []

    def get_top_stocks_by_change_rate(
        self,
        target_date: date | None = None,
        market: str = "KOSPI",
        top_n: int = 10,
        ascending: bool = False,
        min_trading_value: int = 1_000_000_000,
    ) -> list[dict]:
        """등락률 상위/하위 종목 조회

        Args:
            target_date: 조회 날짜 (기본값: 최근 거래일)
            market: 시장 (KOSPI, KOSDAQ)
            top_n: 상위 N개
            ascending: True면 하락률 상위, False면 상승률 상위
            min_trading_value: 최소 거래대금 (기본 10억)

        Returns:
            [{"code": "005930", "name": "삼성전자", "trading_value": 1000000000, "change_rate": 2.5}, ...]
        """
        # 거래대금 상위 종목 데이터 재활용 (이미 수집된 데이터 사용)
        all_stocks = self.get_top_stocks_by_trading_value(
            target_date=target_date,
            market=market,
            top_n=100,  # 충분히 많은 종목 가져오기
        )

        if not all_stocks:
            return []

        # 거래대금 필터
        filtered = [s for s in all_stocks if s["trading_value"] >= min_trading_value]

        # 등락률 기준 정렬
        filtered.sort(key=lambda x: x["change_rate"], reverse=not ascending)

        return filtered[:top_n]

    def get_market_summary(
        self,
        target_date: date | None = None,
        top_n: int = 5,
    ) -> dict:
        """시장 요약 정보 (거래대금/상승률/하락률 상위)

        Returns:
            {
                "date": "2026-01-29",
                "top_trading_value": [...],
                "top_gainers": [...],
                "top_losers": [...],
            }
        """
        if target_date is None:
            target_date = date.today()

        return {
            "date": target_date.isoformat(),
            "top_trading_value": self.get_top_stocks_by_trading_value(target_date, top_n=top_n),
            "top_gainers": self.get_top_stocks_by_change_rate(target_date, top_n=top_n, ascending=False),
            "top_losers": self.get_top_stocks_by_change_rate(target_date, top_n=top_n, ascending=True),
        }
