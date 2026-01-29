"""기술적 지표 테스트"""

from datetime import date, timedelta

import pandas as pd
import pytest

from stock_analyzer.indicators.technical import TechnicalIndicatorCalculator
from stock_analyzer.models import PriceData, SignalType, TechnicalIndicators


def generate_price_data(count: int = 50, base_price: float = 50000) -> list[PriceData]:
    """테스트용 가격 데이터 생성"""
    import random

    random.seed(42)
    data = []
    price = base_price

    for i in range(count):
        change = random.uniform(-0.03, 0.03)
        price = price * (1 + change)

        high = price * random.uniform(1.0, 1.02)
        low = price * random.uniform(0.98, 1.0)
        open_price = random.uniform(low, high)

        data.append(
            PriceData(
                date=date.today() - timedelta(days=count - i),
                open=open_price,
                high=high,
                low=low,
                close=price,
                volume=random.randint(1000000, 10000000),
                trading_value=random.uniform(1e10, 1e11),
                change_rate=change * 100,
            )
        )

    return data


class TestTechnicalIndicatorCalculator:
    """기술적 지표 계산기 테스트"""

    def test_calculate_rsi(self):
        """RSI 계산"""
        calculator = TechnicalIndicatorCalculator()
        price_data = generate_price_data(50)

        close = pd.Series([p.close for p in price_data])
        rsi = calculator.calculate_rsi(close)

        # RSI는 0-100 사이
        valid_rsi = rsi.dropna()
        assert all(0 <= v <= 100 for v in valid_rsi)

    def test_calculate_trix(self):
        """TRIX 계산"""
        calculator = TechnicalIndicatorCalculator()
        price_data = generate_price_data(50)

        close = pd.Series([p.close for p in price_data])
        trix, trix_signal = calculator.calculate_trix(close)

        # 값이 계산되어야 함
        assert len(trix) == len(close)
        assert len(trix_signal) == len(close)

    def test_calculate_macd(self):
        """MACD 계산"""
        calculator = TechnicalIndicatorCalculator()
        price_data = generate_price_data(50)

        close = pd.Series([p.close for p in price_data])
        macd, signal, histogram = calculator.calculate_macd(close)

        # 값이 계산되어야 함
        assert len(macd) == len(close)
        assert len(signal) == len(close)
        assert len(histogram) == len(close)

    def test_calculate_all(self):
        """모든 지표 계산"""
        calculator = TechnicalIndicatorCalculator()
        price_data = generate_price_data(50)

        indicators = calculator.calculate_all(price_data)

        assert len(indicators) == len(price_data)
        assert all(isinstance(ind, TechnicalIndicators) for ind in indicators)

    def test_generate_rsi_buy_signal(self):
        """RSI 매수 시그널 생성 (과매도)"""
        calculator = TechnicalIndicatorCalculator()

        # RSI < 30 인 상황 시뮬레이션
        indicators = [
            TechnicalIndicators(date=date.today() - timedelta(days=1), rsi=35.0),
            TechnicalIndicators(date=date.today(), rsi=25.0),  # 과매도
        ]

        signals = calculator.generate_signals(indicators)

        rsi_signals = [s for s in signals if s.indicator == "RSI"]
        assert len(rsi_signals) == 1
        assert rsi_signals[0].signal == SignalType.BUY

    def test_generate_rsi_sell_signal(self):
        """RSI 매도 시그널 생성 (과매수)"""
        calculator = TechnicalIndicatorCalculator()

        # RSI > 70 인 상황 시뮬레이션
        indicators = [
            TechnicalIndicators(date=date.today() - timedelta(days=1), rsi=65.0),
            TechnicalIndicators(date=date.today(), rsi=75.0),  # 과매수
        ]

        signals = calculator.generate_signals(indicators)

        rsi_signals = [s for s in signals if s.indicator == "RSI"]
        assert len(rsi_signals) == 1
        assert rsi_signals[0].signal == SignalType.SELL

    def test_generate_macd_golden_cross(self):
        """MACD 골든크로스 시그널"""
        calculator = TechnicalIndicatorCalculator()

        # MACD가 시그널 상향 돌파
        indicators = [
            TechnicalIndicators(
                date=date.today() - timedelta(days=1),
                macd=-100.0,
                macd_signal=-50.0,
            ),
            TechnicalIndicators(
                date=date.today(),
                macd=100.0,  # 상향 돌파
                macd_signal=50.0,
            ),
        ]

        signals = calculator.generate_signals(indicators)

        macd_signals = [s for s in signals if s.indicator == "MACD"]
        assert len(macd_signals) == 1
        assert macd_signals[0].signal == SignalType.BUY

    def test_generate_macd_dead_cross(self):
        """MACD 데드크로스 시그널"""
        calculator = TechnicalIndicatorCalculator()

        # MACD가 시그널 하향 돌파
        indicators = [
            TechnicalIndicators(
                date=date.today() - timedelta(days=1),
                macd=100.0,
                macd_signal=50.0,
            ),
            TechnicalIndicators(
                date=date.today(),
                macd=-100.0,  # 하향 돌파
                macd_signal=-50.0,
            ),
        ]

        signals = calculator.generate_signals(indicators)

        macd_signals = [s for s in signals if s.indicator == "MACD"]
        assert len(macd_signals) == 1
        assert macd_signals[0].signal == SignalType.SELL

    def test_empty_price_data(self):
        """빈 데이터 처리"""
        calculator = TechnicalIndicatorCalculator()

        indicators = calculator.calculate_all([])
        assert indicators == []

        signals = calculator.generate_signals([])
        assert signals == []

    def test_single_data_point(self):
        """단일 데이터 포인트"""
        calculator = TechnicalIndicatorCalculator()

        indicators = [
            TechnicalIndicators(date=date.today(), rsi=50.0),
        ]

        signals = calculator.generate_signals(indicators)
        assert signals == []  # 비교할 이전 데이터가 없음
