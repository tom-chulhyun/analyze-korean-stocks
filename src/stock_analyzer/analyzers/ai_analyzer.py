"""OpenAI 기반 AI 분석기"""

import json

from openai import OpenAI

from stock_analyzer.config import get_settings
from stock_analyzer.models import AIAnalysis, NewsArticle


class AIAnalyzer:
    """OpenAI 기반 AI 분석기"""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        settings = get_settings()
        self._client: OpenAI | None = None
        self._model = model

        if settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key)

    @property
    def is_available(self) -> bool:
        """AI 분석 사용 가능 여부"""
        return self._client is not None

    def analyze(
        self,
        stock_name: str,
        articles: list[NewsArticle],
        report_data: dict,
    ) -> AIAnalysis | None:
        """전체 AI 분석 수행"""
        if not self._client:
            return None

        try:
            # 뉴스 요약
            news_summary = self.summarize_news(stock_name, articles)

            # 감성 분석
            sentiment, sentiment_score, key_issues = self.analyze_sentiment(stock_name, articles)

            # 종합 의견 생성
            overall_opinion = self.generate_opinion(stock_name, report_data, news_summary)

            return AIAnalysis(
                news_summary=news_summary,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                key_issues=key_issues,
                overall_opinion=overall_opinion,
            )

        except Exception as e:
            # AI 분석 실패 시 None 반환
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
        except Exception:
            return "뉴스 요약 생성 실패"

    def analyze_sentiment(
        self,
        stock_name: str,
        articles: list[NewsArticle],
    ) -> tuple[str, float, list[str]]:
        """감성 분석"""
        if not self._client or not articles:
            return "NEUTRAL", 0.0, []

        news_text = "\n".join(
            [f"- {a.title}" for a in articles[:10]]
        )

        prompt = f"""다음은 {stock_name} 관련 최근 뉴스 헤드라인입니다.
뉴스의 전반적인 감성과 주요 이슈를 분석해주세요.

뉴스 목록:
{news_text}

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

        except Exception:
            return "NEUTRAL", 0.0, []

    def generate_opinion(
        self,
        stock_name: str,
        report_data: dict,
        news_summary: str,
    ) -> str:
        """종합 의견 생성"""
        if not self._client:
            return "AI 분석 불가"

        # 리포트 데이터에서 핵심 정보 추출
        latest_price = report_data.get("latest_price", {})
        signals = report_data.get("signals", [])
        financials = report_data.get("financials", [])

        signals_text = "\n".join(
            [f"- {s.get('indicator', '')}: {s.get('signal', '')} ({s.get('reason', '')})" for s in signals]
        ) if signals else "시그널 없음"

        financials_text = ""
        for f in financials[:2]:
            financials_text += f"- {f.get('year', '')}년: 매출 {f.get('revenue', 'N/A')}, 영업이익 {f.get('operating_income', 'N/A')}\n"

        prompt = f"""다음은 {stock_name}의 분석 데이터입니다. 종합적인 투자 의견을 작성해주세요.

## 최근 주가
- 종가: {latest_price.get('close', 'N/A')}원
- 등락률: {latest_price.get('change_rate', 'N/A')}%

## 기술적 시그널
{signals_text}

## 재무 현황
{financials_text}

## 뉴스 요약
{news_summary}

위 정보를 종합하여 투자자에게 도움이 될 수 있는 의견을 4-5문장으로 작성해주세요.
단, 투자 권유가 아닌 정보 제공 목적임을 명시하고, 투자 결정은 개인의 판단임을 언급해주세요.

종합 의견:"""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 객관적인 주식 시장 애널리스트입니다. 과도한 낙관이나 비관 없이 균형 잡힌 의견을 제시하세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
                temperature=0.4,
            )
            return response.choices[0].message.content or "종합 의견 생성 실패"
        except Exception:
            return "종합 의견 생성 실패"
