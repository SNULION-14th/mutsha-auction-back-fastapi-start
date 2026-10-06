"""애플리케이션 설정 (환경변수 로딩).

Django의 `settings.py` + `django-environ` 역할을 pydantic-settings로 대체합니다.
`.env` 파일이나 실제 환경변수에서 값을 읽어옵니다.
"""
from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- 보안/JWT ---
    SECRET_KEY: str = "django-insecure-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_LIFETIME_MINUTES: int = 30
    REFRESH_TOKEN_LIFETIME_DAYS: int = 1

    # --- 데이터베이스 ---
    DATABASE_URL: str = "sqlite:///./db.sqlite3"

    # --- 미디어 ---
    MEDIA_URL: str = "/media/"
    MEDIA_ROOT: str = "media"

    # --- 카카오 로그인 ---
    KAKAO_SECRET_KEY: str = ""
    KAKAO_REDIRECT_URI: str = "http://localhost:8000/api/user/kakao/callback"

    # --- 카카오페이 ---
    KAKAO_PAY_KEY: str = ""
    KAKAO_PAY_CID: str = "TC0ONETIME"

    # --- CORS ---
    CORS_ALLOW_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def access_token_lifetime(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_LIFETIME_MINUTES)

    @property
    def refresh_token_lifetime(self) -> timedelta:
        return timedelta(days=self.REFRESH_TOKEN_LIFETIME_DAYS)


settings = Settings()
