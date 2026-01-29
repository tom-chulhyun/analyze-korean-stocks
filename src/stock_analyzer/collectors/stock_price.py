"""주가 데이터 수집기 (pykrx)"""

from datetime import date, timedelta

import pandas as pd
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

        return StockInfo(code=code, name=name, market=market)

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
