"""기술적 지표 계산 모듈"""

import pandas as pd
import pandas_ta as ta

from stock_analyzer.models import PriceData, Signal, SignalType, TechnicalIndicators


class TechnicalIndicatorCalculator:
    """기술적 지표 계산기"""

    def __init__(
        self,
        rsi_length: int = 14,
        trix_length: int = 15,
        trix_signal: int = 9,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
    ) -> None:
        self.rsi_length = rsi_length
        self.trix_length = trix_length
        self.trix_signal = trix_signal
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal

    def calculate_all(
        self,
        price_data: list[PriceData],
    ) -> list[TechnicalIndicators]:
        """모든 기술적 지표 계산"""
        if not price_data:
            return []

        # DataFrame으로 변환
        df = pd.DataFrame([p.model_dump() for p in price_data])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        close = df["close"]

        # RSI 계산
        rsi = self.calculate_rsi(close)

        # TRIX 계산
        trix, trix_sig = self.calculate_trix(close)

        # MACD 계산
        macd, macd_sig, macd_hist = self.calculate_macd(close)

        # TechnicalIndicators 리스트로 변환
        indicators = []
        for i, date in enumerate(df.index):
            indicators.append(
                TechnicalIndicators(
                    date=date.date(),
                    rsi=self._safe_float(rsi.iloc[i]) if i < len(rsi) else None,
                    trix=self._safe_float(trix.iloc[i]) if i < len(trix) else None,
                    trix_signal=self._safe_float(trix_sig.iloc[i]) if i < len(trix_sig) else None,
                    macd=self._safe_float(macd.iloc[i]) if i < len(macd) else None,
                    macd_signal=self._safe_float(macd_sig.iloc[i]) if i < len(macd_sig) else None,
                    macd_histogram=self._safe_float(macd_hist.iloc[i]) if i < len(macd_hist) else None,
                )
            )

        return indicators

    def calculate_rsi(
        self,
        close: pd.Series,
        length: int | None = None,
    ) -> pd.Series:
        """RSI 계산"""
        length = length or self.rsi_length
        result = ta.rsi(close, length=length)
        if result is None:
            return pd.Series([None] * len(close), index=close.index)
        return result

    def calculate_trix(
        self,
        close: pd.Series,
        length: int | None = None,
        signal: int | None = None,
    ) -> tuple[pd.Series, pd.Series]:
        """TRIX + 시그널 계산"""
        length = length or self.trix_length
        signal = signal or self.trix_signal

        trix_df = ta.trix(close, length=length, signal=signal)

        if trix_df is None or trix_df.empty:
            empty = pd.Series([None] * len(close), index=close.index)
            return empty, empty

        trix_col = f"TRIX_{length}_{signal}"
        signal_col = f"TRIXs_{length}_{signal}"

        trix = trix_df[trix_col] if trix_col in trix_df.columns else trix_df.iloc[:, 0]
        trix_sig = trix_df[signal_col] if signal_col in trix_df.columns else trix_df.iloc[:, 1]

        return trix, trix_sig

    def calculate_macd(
        self,
        close: pd.Series,
        fast: int | None = None,
        slow: int | None = None,
        signal: int | None = None,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """MACD, 시그널, 히스토그램 계산"""
        fast = fast or self.macd_fast
        slow = slow or self.macd_slow
        signal = signal or self.macd_signal

        macd_df = ta.macd(close, fast=fast, slow=slow, signal=signal)

        if macd_df is None or macd_df.empty:
            empty = pd.Series([None] * len(close), index=close.index)
            return empty, empty, empty

        macd_col = f"MACD_{fast}_{slow}_{signal}"
        signal_col = f"MACDs_{fast}_{slow}_{signal}"
        hist_col = f"MACDh_{fast}_{slow}_{signal}"

        macd = macd_df[macd_col] if macd_col in macd_df.columns else macd_df.iloc[:, 0]
        macd_sig = macd_df[signal_col] if signal_col in macd_df.columns else macd_df.iloc[:, 1]
        macd_hist = macd_df[hist_col] if hist_col in macd_df.columns else macd_df.iloc[:, 2]

        return macd, macd_sig, macd_hist

    def generate_signals(
        self,
        indicators: list[TechnicalIndicators],
    ) -> list[Signal]:
        """매매 시그널 생성"""
        if len(indicators) < 2:
            return []

        signals = []
        latest = indicators[-1]
        prev = indicators[-2]

        # RSI 시그널
        if latest.rsi is not None:
            rsi_signal = self._generate_rsi_signal(latest.rsi, prev.rsi)
            if rsi_signal:
                signals.append(rsi_signal)

        # TRIX 시그널
        if latest.trix is not None and latest.trix_signal is not None:
            trix_signal = self._generate_trix_signal(
                latest.trix,
                latest.trix_signal,
                prev.trix,
                prev.trix_signal,
            )
            if trix_signal:
                signals.append(trix_signal)

        # MACD 시그널
        if latest.macd is not None and latest.macd_signal is not None:
            macd_signal = self._generate_macd_signal(
                latest.macd,
                latest.macd_signal,
                prev.macd,
                prev.macd_signal,
            )
            if macd_signal:
                signals.append(macd_signal)

        return signals

    def _generate_rsi_signal(
        self,
        current_rsi: float,
        prev_rsi: float | None,
    ) -> Signal | None:
        """RSI 시그널 생성"""
        if current_rsi < 30:
            # 과매도 구간
            strength = min(5, int((30 - current_rsi) / 6) + 1)
            return Signal(
                indicator="RSI",
                signal=SignalType.BUY,
                reason=f"RSI {current_rsi:.1f} - 과매도 구간 진입",
                strength=strength,
            )
        elif current_rsi > 70:
            # 과매수 구간
            strength = min(5, int((current_rsi - 70) / 6) + 1)
            return Signal(
                indicator="RSI",
                signal=SignalType.SELL,
                reason=f"RSI {current_rsi:.1f} - 과매수 구간 진입",
                strength=strength,
            )
        elif prev_rsi is not None:
            # 과매도/과매수 탈출
            if prev_rsi < 30 <= current_rsi:
                return Signal(
                    indicator="RSI",
                    signal=SignalType.BUY,
                    reason=f"RSI {current_rsi:.1f} - 과매도 구간 탈출",
                    strength=2,
                )
            elif prev_rsi > 70 >= current_rsi:
                return Signal(
                    indicator="RSI",
                    signal=SignalType.SELL,
                    reason=f"RSI {current_rsi:.1f} - 과매수 구간 탈출",
                    strength=2,
                )

        return None

    def _generate_trix_signal(
        self,
        current_trix: float,
        current_signal: float,
        prev_trix: float | None,
        prev_signal: float | None,
    ) -> Signal | None:
        """TRIX 시그널 생성"""
        if prev_trix is None or prev_signal is None:
            return None

        # 골든 크로스 (TRIX가 시그널 상향 돌파)
        if prev_trix <= prev_signal and current_trix > current_signal:
            strength = min(5, int(abs(current_trix - current_signal) * 10) + 2)
            return Signal(
                indicator="TRIX",
                signal=SignalType.BUY,
                reason=f"TRIX 골든크로스 - 시그널 상향 돌파",
                strength=strength,
            )

        # 데드 크로스 (TRIX가 시그널 하향 돌파)
        if prev_trix >= prev_signal and current_trix < current_signal:
            strength = min(5, int(abs(current_trix - current_signal) * 10) + 2)
            return Signal(
                indicator="TRIX",
                signal=SignalType.SELL,
                reason=f"TRIX 데드크로스 - 시그널 하향 돌파",
                strength=strength,
            )

        # 0선 돌파
        if prev_trix <= 0 < current_trix:
            return Signal(
                indicator="TRIX",
                signal=SignalType.BUY,
                reason="TRIX 0선 상향 돌파",
                strength=2,
            )
        elif prev_trix >= 0 > current_trix:
            return Signal(
                indicator="TRIX",
                signal=SignalType.SELL,
                reason="TRIX 0선 하향 돌파",
                strength=2,
            )

        return None

    def _generate_macd_signal(
        self,
        current_macd: float,
        current_signal: float,
        prev_macd: float | None,
        prev_signal: float | None,
    ) -> Signal | None:
        """MACD 시그널 생성"""
        if prev_macd is None or prev_signal is None:
            return None

        # 골든 크로스 (MACD가 시그널 상향 돌파)
        if prev_macd <= prev_signal and current_macd > current_signal:
            strength = min(5, int(abs(current_macd - current_signal) / 100) + 2)
            return Signal(
                indicator="MACD",
                signal=SignalType.BUY,
                reason="MACD 골든크로스 - 시그널 상향 돌파",
                strength=strength,
            )

        # 데드 크로스 (MACD가 시그널 하향 돌파)
        if prev_macd >= prev_signal and current_macd < current_signal:
            strength = min(5, int(abs(current_macd - current_signal) / 100) + 2)
            return Signal(
                indicator="MACD",
                signal=SignalType.SELL,
                reason="MACD 데드크로스 - 시그널 하향 돌파",
                strength=strength,
            )

        # 0선 돌파
        if prev_macd <= 0 < current_macd:
            return Signal(
                indicator="MACD",
                signal=SignalType.BUY,
                reason="MACD 0선 상향 돌파",
                strength=2,
            )
        elif prev_macd >= 0 > current_macd:
            return Signal(
                indicator="MACD",
                signal=SignalType.SELL,
                reason="MACD 0선 하향 돌파",
                strength=2,
            )

        return None

    @staticmethod
    def _safe_float(value: float | None) -> float | None:
        """NaN을 None으로 변환"""
        if value is None:
            return None
        if pd.isna(value):
            return None
        return float(value)
