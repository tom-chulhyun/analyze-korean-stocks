"""Pydantic 데이터 모델"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class StockInfo(BaseModel):
    """종목 기본 정보"""

    code: str = Field(..., description="종목코드 (6자리)")
    name: str = Field(..., description="종목명")
    market: str = Field(..., description="시장 (KOSPI/KOSDAQ)")


class PriceData(BaseModel):
    """일별 가격 데이터"""

    date: date
    open: float = Field(..., description="시가")
    high: float = Field(..., description="고가")
    low: float = Field(..., description="저가")
    close: float = Field(..., description="종가")
    volume: int = Field(..., description="거래량")
    trading_value: float = Field(..., description="거래대금")
    change_rate: float = Field(..., description="등락률 (%)")


class TechnicalIndicators(BaseModel):
    """기술적 지표"""

    date: date
    rsi: float | None = Field(None, description="RSI (14일)")
    trix: float | None = Field(None, description="TRIX (15일)")
    trix_signal: float | None = Field(None, description="TRIX 시그널 (9일)")
    macd: float | None = Field(None, description="MACD")
    macd_signal: float | None = Field(None, description="MACD 시그널")
    macd_histogram: float | None = Field(None, description="MACD 히스토그램")


class SignalType(str, Enum):
    """시그널 유형"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Signal(BaseModel):
    """매매 시그널"""

    indicator: str = Field(..., description="지표명 (RSI, TRIX, MACD)")
    signal: SignalType = Field(..., description="시그널 유형")
    reason: str = Field(..., description="시그널 발생 이유")
    strength: int = Field(..., ge=1, le=5, description="시그널 강도 (1-5)")


class FinancialData(BaseModel):
    """재무 데이터"""

    year: int = Field(..., description="연도")
    quarter: str | None = Field(None, description="분기 (Q1-Q4 또는 Annual)")
    revenue: float | None = Field(None, description="매출액")
    operating_income: float | None = Field(None, description="영업이익")
    net_income: float | None = Field(None, description="당기순이익")
    per: float | None = Field(None, description="PER")
    pbr: float | None = Field(None, description="PBR")
    roe: float | None = Field(None, description="ROE (%)")


class Disclosure(BaseModel):
    """DART 공시"""

    title: str = Field(..., description="공시 제목")
    date: str = Field(..., description="공시일 (YYYYMMDD)")
    link: str = Field(..., description="공시 링크")
    filer: str = Field(..., description="공시자")


class NewsArticle(BaseModel):
    """뉴스 기사"""

    title: str = Field(..., description="기사 제목")
    link: str = Field(..., description="기사 링크")
    source: str = Field(..., description="언론사")
    published_at: datetime = Field(..., description="발행일시")
    summary: str | None = Field(None, description="요약")


class AIAnalysis(BaseModel):
    """AI 분석 결과"""

    news_summary: str = Field(..., description="뉴스 핵심 요약")
    sentiment: str = Field(..., description="감성 (POSITIVE/NEGATIVE/NEUTRAL)")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="감성 점수")
    key_issues: list[str] = Field(default_factory=list, description="주요 이슈")
    overall_opinion: str = Field(..., description="종합 의견")


class StockReport(BaseModel):
    """종합 리포트"""

    stock_info: StockInfo
    price_data: list[PriceData]
    indicators: list[TechnicalIndicators]
    signals: list[Signal]
    financials: list[FinancialData]
    news: list[NewsArticle]
    disclosures: list[Disclosure] = Field(default_factory=list)
    ai_analysis: AIAnalysis | None = None
    generated_at: datetime = Field(default_factory=datetime.now)
    period_start: date
    period_end: date

    @property
    def latest_price(self) -> PriceData | None:
        """가장 최근 가격 데이터"""
        return self.price_data[-1] if self.price_data else None

    @property
    def latest_indicators(self) -> TechnicalIndicators | None:
        """가장 최근 기술적 지표"""
        return self.indicators[-1] if self.indicators else None
