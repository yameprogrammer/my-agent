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
