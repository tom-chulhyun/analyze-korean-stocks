"""네이버 뉴스 수집기 (검색 API)"""

import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from html import unescape

import requests

from stock_analyzer.config import get_settings
from stock_analyzer.models import NewsArticle


class NewsCollector:
    """네이버 뉴스 수집기"""

    NAVER_NEWS_API_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._session = requests.Session()

        if self._settings.has_naver:
            self._session.headers.update(
                {
                    "X-Naver-Client-Id": self._settings.naver_client_id,
                    "X-Naver-Client-Secret": self._settings.naver_client_secret,
                }
            )

    @property
    def is_available(self) -> bool:
        """네이버 API 사용 가능 여부"""
        return self._settings.has_naver

    def search_news(
        self,
        keyword: str,
        months: int = 6,
        max_results: int = 30,
    ) -> list[NewsArticle]:
        """네이버 뉴스 검색 (최근 N개월)"""
        if not self.is_available:
            return []

        articles = []
        start = 1
        display = 100  # 한 번에 가져올 개수 (최대 100)

        # 기간 설정 (최근 N개월)
        cutoff_date = datetime.now() - timedelta(days=months * 30)

        while len(articles) < max_results and start <= 1000:
            try:
                params = {
                    "query": keyword,
                    "display": display,
                    "start": start,
                    "sort": "date",  # 최신순
                }

                response = self._session.get(
                    self.NAVER_NEWS_API_URL,
                    params=params,
                    timeout=10,
                )
                response.raise_for_status()

                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                for item in items:
                    article = self._parse_news_item(item)
                    if article:
                        # 기간 필터링
                        if article.published_at >= cutoff_date:
                            articles.append(article)

                        if len(articles) >= max_results:
                            break

                start += display

                # 더 이상 결과가 없으면 종료
                if len(items) < display:
                    break

            except Exception:
                break

        return articles

    def deduplicate_news(
        self,
        articles: list[NewsArticle],
        similarity_threshold: float = 0.7,
        max_results: int = 10,
    ) -> list[NewsArticle]:
        """제목 유사도 기반 중복 제거"""
        if not articles:
            return []

        unique_articles = []

        for article in articles:
            is_duplicate = False

            for unique in unique_articles:
                similarity = self._title_similarity(article.title, unique.title)
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(article)

            if len(unique_articles) >= max_results:
                break

        return unique_articles

    def _parse_news_item(self, item: dict) -> NewsArticle | None:
        """뉴스 아이템 파싱"""
        try:
            # 제목 (HTML 태그 제거)
            title = self._clean_html(item.get("title", ""))
            if not title:
                return None

            # 링크
            link = item.get("originallink") or item.get("link", "")

            # 요약 (HTML 태그 제거)
            summary = self._clean_html(item.get("description", ""))

            # 발행일 파싱
            pub_date_str = item.get("pubDate", "")
            published_at = self._parse_date(pub_date_str)

            # 언론사 추출 (링크에서)
            source = self._extract_source(link)

            return NewsArticle(
                title=title,
                link=link,
                source=source,
                published_at=published_at,
                summary=summary,
            )

        except Exception:
            return None

    def _clean_html(self, text: str) -> str:
        """HTML 태그 및 엔티티 제거"""
        # HTML 엔티티 디코딩
        text = unescape(text)
        # HTML 태그 제거
        text = re.sub(r"<[^>]+>", "", text)
        # 연속 공백 정리
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _parse_date(self, date_str: str) -> datetime:
        """날짜 문자열 파싱 (RFC 2822 형식)"""
        # 예: "Mon, 27 Jan 2025 09:00:00 +0900"
        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(date_str)
            # timezone-naive로 변환 (비교를 위해)
            return dt.replace(tzinfo=None)
        except Exception:
            return datetime.now()

    def _extract_source(self, url: str) -> str:
        """URL에서 언론사 추출"""
        try:
            from urllib.parse import urlparse

            domain = urlparse(url).netloc
            # 주요 언론사 매핑
            source_map = {
                "news.naver.com": "네이버뉴스",
                "n.news.naver.com": "네이버뉴스",
                "www.chosun.com": "조선일보",
                "www.donga.com": "동아일보",
                "www.joongang.co.kr": "중앙일보",
                "www.hani.co.kr": "한겨레",
                "www.khan.co.kr": "경향신문",
                "www.mk.co.kr": "매일경제",
                "www.hankyung.com": "한국경제",
                "www.sedaily.com": "서울경제",
                "www.fnnews.com": "파이낸셜뉴스",
                "www.edaily.co.kr": "이데일리",
                "www.mt.co.kr": "머니투데이",
                "www.etnews.com": "전자신문",
                "www.zdnet.co.kr": "지디넷코리아",
                "www.bloter.net": "블로터",
                "www.yonhapnews.co.kr": "연합뉴스",
                "www.yna.co.kr": "연합뉴스",
                "news.sbs.co.kr": "SBS",
                "news.kbs.co.kr": "KBS",
                "imnews.imbc.com": "MBC",
            }

            for key, name in source_map.items():
                if key in domain:
                    return name

            # 매핑 없으면 도메인 반환
            return domain.replace("www.", "").split(".")[0]

        except Exception:
            return "Unknown"

    def _title_similarity(self, title1: str, title2: str) -> float:
        """두 제목의 유사도 계산"""
        # 특수문자 제거 및 소문자 변환
        clean1 = re.sub(r"[^\w\s]", "", title1.lower())
        clean2 = re.sub(r"[^\w\s]", "", title2.lower())

        return SequenceMatcher(None, clean1, clean2).ratio()
