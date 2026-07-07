from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Database Settings
    # 기본값은 로컬 개발용(docker-compose와 일치)으로 지정하고, 실 서버 환경에서는 .env나 OS 환경변수로 덮어씌웁니다.
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@127.0.0.1:5432/novel_db"
    
    # JWT Authentication Settings
    JWT_SECRET: str = "dev-secret-key-do-not-use-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenAI API Key (향후 에이전트 작동 시 필수)
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # ---------------------------------------------------
    # 이메일(SMTP) 설정 - 회원가입 승인 알림 발송에 사용
    # ---------------------------------------------------
    # SMTP 서버 호스트 (예: smtp.gmail.com)
    SMTP_HOST: str = "smtp.gmail.com"
    # SMTP 포트 (587: STARTTLS, 465: SSL)
    SMTP_PORT: int = 587
    # 발신자 이메일 주소
    SMTP_USER: Optional[str] = None
    # 발신자 앱 비밀번호 (Gmail의 경우 '앱 비밀번호' 사용)
    SMTP_PASSWORD: Optional[str] = None
    # 발신자 표시 이름
    SMTP_FROM_NAME: str = "AI 소설 작가 시스템"

    # ---------------------------------------------------
    # 관리자 설정
    # ---------------------------------------------------
    # 회원가입 승인 요청 이메일을 수신할 관리자 이메일
    ADMIN_EMAIL: Optional[str] = None
    # 서비스 베이스 URL (승인 링크 생성에 사용)
    BASE_URL: str = "http://localhost:8000"

    # Pydantic Settings Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # 설정되지 않은 시스템 환경변수는 무시하여 에러 방지
    )

settings = Settings()


import logging
logger = logging.getLogger(__name__)
if settings.JWT_SECRET == "dev-secret-key-do-not-use-in-production":
    logger.warning("WARNING: Using default dev JWT_SECRET. Must be overridden in production!")
