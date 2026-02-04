"""OpenAI 기반 AI 분석기"""

import json

from openai import OpenAI
from rich.console import Console

from stock_analyzer.config import get_settings
from stock_analyzer.models import AIAnalysis, Disclosure, NewsArticle

console = Console(stderr=True)


class AIAnalyzer:
    """OpenAI 기반 AI 분석기"""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        settings = get_settings()
        self._client: OpenAI | None = None
        self._model = model

        if settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key)
        else:
            console.print("  [yellow]⚠ OPENAI_API_KEY 미설정 - AI 분석 비활성화[/yellow]")

    @property
    def is_available(self) -> bool:
        """AI 분석 사용 가능 여부"""
        return self._client is not None

    def analyze(
        self,
        stock_name: str,
        articles: list[NewsArticle],
        disclosures: list[Disclosure],
        report_data: dict,
    ) -> AIAnalysis | None:
        """전체 AI 분석 수행"""
        if not self._client:
            return None

        try:
            # 뉴스 요약
            news_summary = self.summarize_news(stock_name, articles)

            # 뉴스 상세 분석
            news_analysis = self.analyze_news(stock_name, articles)

            # 공시 분석
            disclosure_analysis = self.analyze_disclosures(stock_name, disclosures)

            # 감성 분석
            sentiment, sentiment_score, key_issues = self.analyze_sentiment(
                stock_name, articles, disclosures
            )

            # 종합 의견 생성
            overall_opinion = self.generate_opinion(
                stock_name, report_data, news_summary, disclosure_analysis
            )

            return AIAnalysis(
                news_summary=news_summary,
                news_analysis=news_analysis,
                disclosure_analysis=disclosure_analysis,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                key_issues=key_issues,
                overall_opinion=overall_opinion,
            )

        except Exception as e:
            console.print(f"  [red]✗ AI 분석 실패: {e}[/red]")
            return None

    def summarize_news(
        self,
        stock_name: str,
        articles: list[NewsArticle],
    ) -> str:
        """뉴스 핵심 요약"""
        if not self._client or not articles:
            return "뉴스 요약 없음"

        news_text = "\n".join(
            [f"- [{a.source}] {a.title}" for a in articles[:10]]
        )

        prompt = f"""다음은 {stock_name} 관련 최근 뉴스 헤드라인입니다.
이 뉴스들의 핵심 내용을 3-4문장으로 요약해주세요.
투자자 관점에서 중요한 정보를 중심으로 작성해주세요.

뉴스 목록:
{news_text}

요약:"""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 주식 시장 뉴스를 분석하는 전문 애널리스트입니다. 간결하고 명확하게 요약해주세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content or "요약 생성 실패"
        except Exception as e:
            console.print(f"  [red]✗ 뉴스 요약 실패: {e}[/red]")
            return "뉴스 요약 생성 실패"

    def analyze_news(
        self,
        stock_name: str,
        articles: list[NewsArticle],
    ) -> str:
        """뉴스 상세 분석 - 투자에 미치는 영향"""
        if not self._client or not articles:
            return ""

        news_text = "\n".join(
            [f"- [{a.source}] {a.title}" for a in articles[:10]]
        )

        prompt = f"""다음은 {stock_name} 관련 최근 뉴스 헤드라인입니다.
투자 관점에서 핵심 내용을 분석해주세요.

뉴스 목록:
{news_text}

분석 요청:
- 사업/실적 관련 핵심 뉴스와 함의
- 시장/업종 동향의 영향
- 투자자 주목 포인트

**5-10문장으로 작성하세요. 번호나 기호 없이 자연스러운 문장으로 작성하세요.**"""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 주식 시장 뉴스를 분석하는 전문 애널리스트입니다. 핵심을 5-10문장으로 분석하세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            console.print(f"  [red]✗ 뉴스 분석 실패: {e}[/red]")
            return ""

    def analyze_disclosures(
        self,
        stock_name: str,
        disclosures: list[Disclosure],
    ) -> str:
        """DART 공시 분석 - 공시 내용의 의미와 영향"""
        if not self._client or not disclosures:
            return ""

        disclosure_text = "\n".join(
            [f"- [{d.date[:4]}-{d.date[4:6]}-{d.date[6:]}] {d.title} (공시자: {d.filer})"
             for d in disclosures[:10]]
        )

        prompt = f"""다음은 {stock_name}의 최근 DART 공시 목록입니다.
투자 관점에서 핵심 내용을 분석해주세요.

공시 목록:
{disclosure_text}

분석 요청:
- 주요 공시의 핵심 내용과 의미
- 재무/경영 관련 시사점
- 투자자 주의 사항

**5-10문장으로 작성하세요. 번호나 기호 없이 자연스러운 문장으로 작성하세요.**"""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 기업 공시 분석 전문가입니다. 핵심을 5-10문장으로 분석하세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            console.print(f"  [red]✗ 공시 분석 실패: {e}[/red]")
            return ""

    def analyze_sentiment(
        self,
        stock_name: str,
        articles: list[NewsArticle],
        disclosures: list[Disclosure] | None = None,
    ) -> tuple[str, float, list[str]]:
        """감성 분석 (뉴스 + 공시)"""
        if not self._client or (not articles and not disclosures):
            return "NEUTRAL", 0.0, []

        news_text = "\n".join(
            [f"- [뉴스] {a.title}" for a in articles[:10]]
        ) if articles else ""

        disclosure_text = "\n".join(
            [f"- [공시] {d.title}" for d in (disclosures or [])[:5]]
        ) if disclosures else ""

        combined_text = f"{news_text}\n{disclosure_text}".strip()

        prompt = f"""다음은 {stock_name} 관련 최근 뉴스 및 DART 공시 목록입니다.
전반적인 감성과 주요 이슈를 분석해주세요.

목록:
{combined_text}

다음 JSON 형식으로 응답해주세요:
{{
    "sentiment": "POSITIVE" 또는 "NEGATIVE" 또는 "NEUTRAL",
    "score": -1.0에서 1.0 사이의 숫자 (음수는 부정, 양수는 긍정),
    "key_issues": ["이슈1", "이슈2", "이슈3"] (최대 5개)
}}

JSON:"""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 주식 시장 뉴스를 분석하는 전문 애널리스트입니다. JSON 형식으로만 응답하세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.2,
            )

            content = response.choices[0].message.content or "{}"
            # JSON 파싱
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            result = json.loads(content.strip())

            sentiment = result.get("sentiment", "NEUTRAL")
            score = float(result.get("score", 0.0))
            key_issues = result.get("key_issues", [])

            return sentiment, score, key_issues

        except Exception as e:
            console.print(f"  [red]✗ 감성 분석 실패: {e}[/red]")
            return "NEUTRAL", 0.0, []

    def generate_opinion(
        self,
        stock_name: str,
        report_data: dict,
        news_summary: str,
        disclosure_analysis: str = "",
    ) -> str:
        """종합 의견 생성"""
        if not self._client:
            return "AI 분석 불가"

        # 리포트 데이터에서 핵심 정보 추출
        latest_price = report_data.get("latest_price", {})
        signals = report_data.get("signals", [])

        signals_text = ", ".join(
            [f"{s.get('indicator', '')}: {s.get('signal', '')}" for s in signals]
        ) if signals else "시그널 없음"

        prompt = f"""다음은 {stock_name}의 핵심 분석 데이터입니다.

- 현재가: {latest_price.get('close', 'N/A')}원 ({latest_price.get('change_rate', 'N/A')}%)
- 기술적 시그널: {signals_text}
- 뉴스 요약: {news_summary[:300] if news_summary else 'N/A'}

위 정보를 바탕으로 종합 투자 의견을 작성해주세요.

**5-10문장으로 작성하세요. 마지막에 "투자 결정은 개인의 판단"임을 언급하세요.**"""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 객관적인 주식 시장 애널리스트입니다. 핵심을 5-10문장으로 분석하세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.4,
            )
            return response.choices[0].message.content or "종합 의견 생성 실패"
        except Exception as e:
            console.print(f"  [red]✗ 종합 의견 생성 실패: {e}[/red]")
            return "종합 의견 생성 실패"
