"""종합 주식 분석기"""

from datetime import date, datetime

from rich.console import Console

from stock_analyzer.analyzers.ai_analyzer import AIAnalyzer
from stock_analyzer.collectors.dart import DartCollector
from stock_analyzer.collectors.news import NewsCollector
from stock_analyzer.collectors.stock_price import StockNotFoundError, StockPriceCollector
from stock_analyzer.indicators.technical import TechnicalIndicatorCalculator
from stock_analyzer.models import Disclosure, StockReport

console = Console()


class StockAnalyzer:
    """종합 주식 분석기"""

    def __init__(self, use_ai: bool = True) -> None:
        self.price_collector = StockPriceCollector()
        self.dart_collector = DartCollector()
        self.news_collector = NewsCollector()
        self.indicator_calculator = TechnicalIndicatorCalculator()
        self.ai_analyzer = AIAnalyzer() if use_ai else None

    def analyze(
        self,
        code: str,
        start: date,
        end: date,
    ) -> StockReport:
        """종합 분석 수행"""
        # 1. 종목 정보 조회
        console.print(f"[bold blue]종목 정보 조회 중...[/bold blue]")
        stock_info = self.price_collector.get_stock_info(code)
        console.print(f"  ✓ {stock_info.name} ({stock_info.code}) - {stock_info.market}")

        # 2. 주가 데이터 조회
        console.print(f"[bold blue]주가 데이터 조회 중...[/bold blue]")
        price_data = self.price_collector.get_ohlcv(code, start, end)
        console.print(f"  ✓ {len(price_data)}일 데이터 수집")

        if not price_data:
            raise ValueError(f"주가 데이터를 찾을 수 없습니다: {code}")

        # 3. 기술적 지표 계산
        console.print(f"[bold blue]기술적 지표 계산 중...[/bold blue]")
        indicators = self.indicator_calculator.calculate_all(price_data)
        signals = self.indicator_calculator.generate_signals(indicators)
        console.print(f"  ✓ RSI, TRIX, MACD 계산 완료")
        if signals:
            for sig in signals:
                console.print(f"  → {sig.indicator}: {sig.signal.value} ({sig.reason})")

        # 4. 재무제표 조회
        console.print(f"[bold blue]재무제표 조회 중...[/bold blue]")
        financials = []
        if self.dart_collector.is_available:
            current_year = date.today().year
            financials = self.dart_collector.get_financial_statements(
                code,
                years=[current_year, current_year - 1],
            )
            console.print(f"  ✓ {len(financials)}개 연도 재무제표 수집")
        else:
            console.print(f"  [yellow]⚠ DART API 키가 설정되지 않음[/yellow]")

        # 4-1. 최근 공시 조회
        console.print(f"[bold blue]최근 공시 조회 중...[/bold blue]")
        disclosures: list[Disclosure] = []
        if self.dart_collector.is_available:
            raw_disclosures = self.dart_collector.get_recent_disclosures(code, count=5)
            for d in raw_disclosures:
                rcept_no = d.get("rcept_no", "")
                disclosures.append(
                    Disclosure(
                        title=d.get("report_nm", ""),
                        date=d.get("rcept_dt", ""),
                        link=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                        filer=d.get("flr_nm", ""),
                    )
                )
            console.print(f"  ✓ {len(disclosures)}건 공시 수집")
        else:
            console.print(f"  [yellow]⚠ DART API 키가 설정되지 않음[/yellow]")

        # 5. 뉴스 수집
        console.print(f"[bold blue]뉴스 수집 중...[/bold blue]")
        all_news = self.news_collector.search_news(stock_info.name, months=6)
        news = self.news_collector.deduplicate_news(all_news, max_results=10)
        console.print(f"  ✓ {len(news)}건 뉴스 수집 (중복 제거)")

        # 6. AI 분석
        ai_analysis = None
        if self.ai_analyzer and self.ai_analyzer.is_available:
            console.print(f"[bold blue]AI 분석 중...[/bold blue]")
            report_data = {
                "latest_price": price_data[-1].model_dump() if price_data else {},
                "signals": [s.model_dump() for s in signals],
                "financials": [f.model_dump() for f in financials],
            }
            ai_analysis = self.ai_analyzer.analyze(
                stock_info.name,
                news,
                report_data,
            )
            if ai_analysis:
                console.print(f"  ✓ 뉴스 요약 및 감성 분석 완료")
                console.print(f"  → 감성: {ai_analysis.sentiment} ({ai_analysis.sentiment_score:+.2f})")
            else:
                console.print(f"  [yellow]⚠ AI 분석 실패[/yellow]")
        else:
            console.print(f"  [yellow]⚠ OpenAI API 키가 설정되지 않음[/yellow]")

        # 7. 리포트 생성
        report = StockReport(
            stock_info=stock_info,
            price_data=price_data,
            indicators=indicators,
            signals=signals,
            financials=financials,
            news=news,
            disclosures=disclosures,
            ai_analysis=ai_analysis,
            generated_at=datetime.now(),
            period_start=start,
            period_end=end,
        )

        console.print(f"[bold green]✓ 분석 완료[/bold green]")

        return report
