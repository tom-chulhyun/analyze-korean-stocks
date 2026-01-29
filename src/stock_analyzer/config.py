"""환경 설정 모듈"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # DART API (필수)
    dart_api_key: str = Field(default="", description="DART API 키")

    # OpenAI API (선택)
    openai_api_key: str | None = Field(default=None, description="OpenAI API 키")

    # 네이버 검색 API (선택)
    naver_client_id: str | None = Field(default=None, description="네이버 Client ID")
    naver_client_secret: str | None = Field(default=None, description="네이버 Client Secret")

    # 카카오톡 API (선택)
    kakao_rest_api_key: str | None = Field(default=None, description="카카오 REST API 키")
    kakao_redirect_uri: str = Field(
        default="http://localhost:8080/callback",
        description="카카오 OAuth 리다이렉트 URI",
    )

    # 출력 설정
    output_dir: Path = Field(
        default=Path("./output"),
        description="리포트 출력 디렉토리",
    )

    # 토큰 저장 경로
    token_dir: Path = Field(
        default=Path.home() / ".stock-analyzer",
        description="OAuth 토큰 저장 디렉토리",
    )

    @property
    def has_openai(self) -> bool:
        """OpenAI API 사용 가능 여부"""
        return bool(self.openai_api_key)

    @property
    def has_naver(self) -> bool:
        """네이버 검색 API 사용 가능 여부"""
        return bool(self.naver_client_id and self.naver_client_secret)

    @property
    def has_kakao(self) -> bool:
        """카카오톡 API 사용 가능 여부"""
        return bool(self.kakao_rest_api_key)

    def ensure_dirs(self) -> None:
        """필요한 디렉토리 생성"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.token_dir.mkdir(parents=True, exist_ok=True)


# 싱글톤 설정 인스턴스
_settings: Settings | None = None


def get_settings() -> Settings:
    """설정 인스턴스 반환"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
