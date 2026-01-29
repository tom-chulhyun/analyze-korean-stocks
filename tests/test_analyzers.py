"""분석기 테스트"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from stock_analyzer.analyzers.ai_analyzer import AIAnalyzer
from stock_analyzer.models import AIAnalysis, NewsArticle


class TestAIAnalyzer:
    """AI 분석기 테스트"""

    def test_is_available_without_key(self):
        """API 키 없을 때 사용 불가"""
        with patch("stock_analyzer.analyzers.ai_analyzer.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = None
            analyzer = AIAnalyzer()
            assert not analyzer.is_available

    def test_analyze_returns_none_without_client(self):
        """클라이언트 없을 때 None 반환"""
        with patch("stock_analyzer.analyzers.ai_analyzer.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = None
            analyzer = AIAnalyzer()

            result = analyzer.analyze("삼성전자", [], {})
            assert result is None

    def test_summarize_news_empty_list(self):
        """빈 뉴스 리스트 요약"""
        with patch("stock_analyzer.analyzers.ai_analyzer.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = None
            analyzer = AIAnalyzer()

            result = analyzer.summarize_news("삼성전자", [])
            assert result == "뉴스 요약 없음"

    def test_analyze_sentiment_empty_list(self):
        """빈 뉴스 리스트 감성 분석"""
        with patch("stock_analyzer.analyzers.ai_analyzer.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = None
            analyzer = AIAnalyzer()

            sentiment, score, issues = analyzer.analyze_sentiment("삼성전자", [])
            assert sentiment == "NEUTRAL"
            assert score == 0.0
            assert issues == []

    @pytest.mark.integration
    def test_full_analysis(self):
        """전체 AI 분석 (통합 테스트 - OpenAI API 키 필요)"""
        analyzer = AIAnalyzer()

        if not analyzer.is_available:
            pytest.skip("OpenAI API 키가 설정되지 않음")

        articles = [
            NewsArticle(
                title="삼성전자 반도체 호황으로 실적 개선 전망",
                link="https://example.com/1",
                source="테스트",
                published_at=datetime.now(),
            ),
            NewsArticle(
                title="삼성전자 AI 반도체 수요 급증",
                link="https://example.com/2",
                source="테스트",
                published_at=datetime.now(),
            ),
        ]

        report_data = {
            "latest_price": {"close": 85000, "change_rate": 2.5},
            "signals": [{"indicator": "RSI", "signal": "HOLD", "reason": "중립"}],
            "financials": [{"year": 2024, "revenue": 300000000000000}],
        }

        result = analyzer.analyze("삼성전자", articles, report_data)

        assert result is not None
        assert isinstance(result, AIAnalysis)
        assert result.news_summary
        assert result.sentiment in ["POSITIVE", "NEGATIVE", "NEUTRAL"]
        assert -1.0 <= result.sentiment_score <= 1.0
        assert result.overall_opinion


class TestStockAnalyzer:
    """종합 분석기 테스트"""

    @pytest.mark.integration
    def test_analyze_samsung(self):
        """삼성전자 분석 (통합 테스트)"""
        from stock_analyzer.analyzers.stock_analyzer import StockAnalyzer

        analyzer = StockAnalyzer(use_ai=False)  # AI 제외

        end = date.today()
        start = end - timedelta(days=30)

        report = analyzer.analyze("005930", start, end)

        assert report.stock_info.code == "005930"
        assert report.stock_info.name == "삼성전자"
        assert len(report.price_data) > 0
        assert len(report.indicators) > 0

    @pytest.mark.integration
    def test_analyze_invalid_code(self):
        """잘못된 종목코드 분석"""
        from stock_analyzer.analyzers.stock_analyzer import StockAnalyzer
        from stock_analyzer.collectors.stock_price import StockNotFoundError

        analyzer = StockAnalyzer(use_ai=False)

        end = date.today()
        start = end - timedelta(days=30)

        with pytest.raises(StockNotFoundError):
            analyzer.analyze("999999", start, end)
