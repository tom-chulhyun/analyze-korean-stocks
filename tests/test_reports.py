"""리포트 생성 테스트"""

from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stock_analyzer.models import (
    AIAnalysis,
    FinancialData,
    NewsArticle,
    PriceData,
    Signal,
    SignalType,
    StockInfo,
    StockReport,
    TechnicalIndicators,
)
from stock_analyzer.reports.generator import ReportGenerator


def create_sample_report() -> StockReport:
    """테스트용 샘플 리포트 생성"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    # 가격 데이터
    price_data = []
    for i in range(30):
        price_data.append(
            PriceData(
                date=start_date + timedelta(days=i),
                open=50000 + i * 100,
                high=51000 + i * 100,
                low=49000 + i * 100,
                close=50500 + i * 100,
                volume=1000000 + i * 10000,
                trading_value=5e10 + i * 1e9,
                change_rate=0.5,
            )
        )

    # 기술적 지표
    indicators = []
    for i, p in enumerate(price_data):
        indicators.append(
            TechnicalIndicators(
                date=p.date,
                rsi=50 + i * 0.5 if i >= 14 else None,
                trix=0.01 * (i - 15) if i >= 15 else None,
                trix_signal=0.005 * (i - 15) if i >= 15 else None,
                macd=100 * (i - 26) if i >= 26 else None,
                macd_signal=50 * (i - 26) if i >= 26 else None,
                macd_histogram=50 * (i - 26) if i >= 26 else None,
            )
        )

    # 시그널
    signals = [
        Signal(
            indicator="RSI",
            signal=SignalType.HOLD,
            reason="RSI 50 - 중립 구간",
            strength=2,
        ),
        Signal(
            indicator="MACD",
            signal=SignalType.BUY,
            reason="MACD 골든크로스",
            strength=3,
        ),
    ]

    # 재무 데이터
    financials = [
        FinancialData(
            year=2024,
            quarter="Annual",
            revenue=300_000_000_000_000,
            operating_income=50_000_000_000_000,
            net_income=40_000_000_000_000,
        ),
        FinancialData(
            year=2023,
            quarter="Annual",
            revenue=280_000_000_000_000,
            operating_income=45_000_000_000_000,
            net_income=35_000_000_000_000,
        ),
    ]

    # 뉴스
    news = [
        NewsArticle(
            title="삼성전자 반도체 호황 전망",
            link="https://example.com/1",
            source="테스트뉴스",
            published_at=datetime.now(),
            summary="반도체 시장 호황이 예상됩니다.",
        ),
        NewsArticle(
            title="삼성전자 AI 반도체 수요 급증",
            link="https://example.com/2",
            source="테스트뉴스",
            published_at=datetime.now() - timedelta(days=1),
        ),
    ]

    # AI 분석
    ai_analysis = AIAnalysis(
        news_summary="삼성전자는 반도체 호황과 AI 수요 증가로 실적 개선이 전망됩니다.",
        sentiment="POSITIVE",
        sentiment_score=0.7,
        key_issues=["반도체 호황", "AI 수요", "실적 개선"],
        overall_opinion="기술적 지표와 뉴스 동향을 종합하면 긍정적인 흐름이 예상됩니다.",
    )

    return StockReport(
        stock_info=StockInfo(code="005930", name="삼성전자", market="KOSPI"),
        price_data=price_data,
        indicators=indicators,
        signals=signals,
        financials=financials,
        news=news,
        ai_analysis=ai_analysis,
        generated_at=datetime.now(),
        period_start=start_date,
        period_end=end_date,
    )


class TestReportGenerator:
    """리포트 생성기 테스트"""

    def test_format_number(self):
        """숫자 포맷팅"""
        assert ReportGenerator._format_number(None) == "-"
        assert ReportGenerator._format_number(1234) == "1,234"
        assert ReportGenerator._format_number(12345678) == "1234만"
        assert ReportGenerator._format_number(123456789012) == "1234억"
        assert ReportGenerator._format_number(1234567890123456) == "12345.68조"

    def test_format_percent(self):
        """퍼센트 포맷팅"""
        assert ReportGenerator._format_percent(None) == "-"
        assert ReportGenerator._format_percent(2.5) == "+2.50%"
        assert ReportGenerator._format_percent(-1.5) == "-1.50%"
        assert ReportGenerator._format_percent(0) == "+0.00%"

    def test_format_date(self):
        """날짜 포맷팅"""
        test_date = date(2024, 12, 25)
        assert ReportGenerator._format_date(test_date) == "2024-12-25"

    def test_create_price_chart(self):
        """가격 차트 생성"""
        generator = ReportGenerator()
        report = create_sample_report()

        chart = generator._create_price_chart(report.price_data)

        assert chart.startswith("data:image/png;base64,")
        assert len(chart) > 100

    def test_create_price_chart_empty(self):
        """빈 데이터 차트"""
        generator = ReportGenerator()

        chart = generator._create_price_chart([])
        assert chart == ""

    def test_create_indicator_chart(self):
        """지표 차트 생성"""
        generator = ReportGenerator()
        report = create_sample_report()

        chart = generator._create_indicator_chart(report.indicators)

        assert chart.startswith("data:image/png;base64,")
        assert len(chart) > 100

    def test_create_indicator_chart_empty(self):
        """빈 지표 차트"""
        generator = ReportGenerator()

        chart = generator._create_indicator_chart([])
        assert chart == ""

    def test_generate_pdf(self, tmp_path):
        """PDF 생성"""
        generator = ReportGenerator()
        report = create_sample_report()

        pdf_path = generator.generate_pdf(report, tmp_path)

        assert pdf_path.exists()
        assert pdf_path.suffix == ".pdf"
        assert pdf_path.stat().st_size > 0

    def test_generate_pdf_filename_format(self, tmp_path):
        """PDF 파일명 형식"""
        generator = ReportGenerator()
        report = create_sample_report()

        pdf_path = generator.generate_pdf(report, tmp_path)

        # 파일명 형식: {종목코드}_{기간}_{날짜}.pdf
        assert report.stock_info.code in pdf_path.stem
        assert pdf_path.suffix == ".pdf"

    def test_generate_pdf_without_ai(self, tmp_path):
        """AI 분석 없는 PDF 생성"""
        generator = ReportGenerator()
        report = create_sample_report()
        report.ai_analysis = None

        pdf_path = generator.generate_pdf(report, tmp_path)

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0

    def test_generate_pdf_without_financials(self, tmp_path):
        """재무 데이터 없는 PDF 생성"""
        generator = ReportGenerator()
        report = create_sample_report()
        report.financials = []

        pdf_path = generator.generate_pdf(report, tmp_path)

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0

    def test_generate_pdf_without_signals(self, tmp_path):
        """시그널 없는 PDF 생성"""
        generator = ReportGenerator()
        report = create_sample_report()
        report.signals = []

        pdf_path = generator.generate_pdf(report, tmp_path)

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
