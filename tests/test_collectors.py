"""데이터 수집기 테스트"""

from datetime import date, datetime, timedelta

import pytest


class TestStockPriceCollector:
    """주가 수집기 테스트"""

    def test_validate_code_format(self):
        """종목코드 형식 검증"""
        from stock_analyzer.collectors.stock_price import StockPriceCollector

        collector = StockPriceCollector()

        # 잘못된 형식
        assert collector.validate_code("12345") is False  # 5자리
        assert collector.validate_code("1234567") is False  # 7자리
        assert collector.validate_code("abcdef") is False  # 문자
        assert collector.validate_code("12345a") is False  # 혼합

    @pytest.mark.integration
    def test_get_stock_info_samsung(self):
        """삼성전자 정보 조회 (통합 테스트)"""
        from stock_analyzer.collectors.stock_price import StockPriceCollector

        collector = StockPriceCollector()
        info = collector.get_stock_info("005930")

        assert info.code == "005930"
        assert info.name == "삼성전자"
        assert info.market == "KOSPI"

    @pytest.mark.integration
    def test_get_stock_info_not_found(self):
        """존재하지 않는 종목 조회 (통합 테스트)"""
        from stock_analyzer.collectors.stock_price import StockNotFoundError, StockPriceCollector

        collector = StockPriceCollector()

        with pytest.raises(StockNotFoundError):
            collector.get_stock_info("999999")

    @pytest.mark.integration
    def test_get_ohlcv(self):
        """OHLCV 데이터 조회 (통합 테스트)"""
        from stock_analyzer.collectors.stock_price import StockPriceCollector

        collector = StockPriceCollector()
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=30)

        price_data = collector.get_ohlcv("005930", start, end)

        assert len(price_data) > 0
        assert all(p.close > 0 for p in price_data)
        assert all(p.volume >= 0 for p in price_data)


class TestNewsCollector:
    """뉴스 수집기 테스트"""

    def test_deduplicate_similar_titles(self):
        """유사한 제목 중복 제거"""
        from stock_analyzer.collectors.news import NewsCollector
        from stock_analyzer.models import NewsArticle

        collector = NewsCollector()

        articles = [
            NewsArticle(
                title="삼성전자 주가 급등, 반도체 호황",
                link="https://example.com/1",
                source="A뉴스",
                published_at=datetime.now(),
            ),
            NewsArticle(
                title="삼성전자 주가 급등...반도체 호황 영향",
                link="https://example.com/2",
                source="B뉴스",
                published_at=datetime.now(),
            ),
            NewsArticle(
                title="SK하이닉스 실적 발표",
                link="https://example.com/3",
                source="C뉴스",
                published_at=datetime.now(),
            ),
        ]

        unique = collector.deduplicate_news(articles, similarity_threshold=0.7)

        # 첫 번째와 두 번째는 유사하므로 하나만 남아야 함
        assert len(unique) == 2

    def test_deduplicate_max_results(self):
        """최대 결과 수 제한"""
        from stock_analyzer.collectors.news import NewsCollector
        from stock_analyzer.models import NewsArticle

        collector = NewsCollector()

        # 완전히 다른 제목들 생성
        titles = [
            "삼성전자 반도체 호황",
            "SK하이닉스 실적 발표",
            "현대차 전기차 판매 급증",
            "LG에너지솔루션 배터리 수출",
            "네이버 AI 서비스 출시",
            "카카오 신규 사업 확장",
            "셀트리온 바이오시밀러 승인",
            "포스코홀딩스 2차전지 소재",
            "삼성바이오로직스 수주 계약",
            "KB금융 배당 확대",
            "신한지주 디지털 전환",
            "하나금융 해외 진출",
            "기아 전기차 생산 확대",
            "LG전자 가전 수출 호조",
            "SK텔레콤 5G 서비스",
        ]

        articles = [
            NewsArticle(
                title=title,
                link=f"https://example.com/{i}",
                source="테스트",
                published_at=datetime.now(),
            )
            for i, title in enumerate(titles)
        ]

        unique = collector.deduplicate_news(articles, max_results=10)

        assert len(unique) == 10

    def test_title_similarity(self):
        """제목 유사도 계산"""
        from stock_analyzer.collectors.news import NewsCollector

        collector = NewsCollector()

        # 동일한 제목
        sim1 = collector._title_similarity("삼성전자 주가", "삼성전자 주가")
        assert sim1 == 1.0

        # 유사한 제목
        sim2 = collector._title_similarity(
            "삼성전자 주가 급등",
            "삼성전자 주가 급등!!"
        )
        assert sim2 > 0.8

        # 다른 제목
        sim3 = collector._title_similarity(
            "삼성전자 주가",
            "SK하이닉스 실적"
        )
        assert sim3 < 0.5

    @pytest.mark.integration
    def test_search_news(self):
        """뉴스 검색 (통합 테스트)"""
        from stock_analyzer.collectors.news import NewsCollector

        collector = NewsCollector()
        articles = collector.search_news("삼성전자", months=1, max_results=5)

        assert len(articles) > 0
        assert all(a.title for a in articles)
        assert all(a.link for a in articles)
