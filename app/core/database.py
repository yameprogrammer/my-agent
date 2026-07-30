from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from app.core.config import settings

# pydantic settings에서 로드된 DB 연결 URL 사용
DATABASE_URL = settings.DATABASE_URL

import os
from sqlalchemy.pool import NullPool

# asyncpg 비동기 엔진 생성
if os.getenv("TESTING") == "True":
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool
    )
else:
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,       # 갤럭시 Z 폴드 4 환경을 고려한 동시 접속 수 풀링
        max_overflow=5
    )

# pgvector 확장 강제 활성화 및 SQLModel 테이블 마이그레이션 함수
async def init_db():
    from app.models import SQLModel  # SQLModel 메타데이터 로드
    async with async_engine.begin() as conn:
        # PostgreSQL pgvector 확장(EXTENSION) 활성화
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # 정의된 모든 테이블 생성
        await conn.run_sync(SQLModel.metadata.create_all)
        # create_all 은 기존 테이블에 컬럼을 추가하지 않음 — Episode RAG 필드 등 soft-migrate
        await conn.execute(text(
            "ALTER TABLE episode ADD COLUMN IF NOT EXISTS rag_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.5"
        ))
        await conn.execute(text(
            "ALTER TABLE episode ADD COLUMN IF NOT EXISTS rag_limit INTEGER NOT NULL DEFAULT 5"
        ))
        await conn.execute(text(
            "ALTER TABLE episode ADD COLUMN IF NOT EXISTS force_reference_ids VARCHAR"
        ))
        # IMP-07: 회차 승인 요약 (장편 연속성)
        await conn.execute(text(
            "ALTER TABLE episode ADD COLUMN IF NOT EXISTS summary TEXT"
        ))
        # IMP-11: 참고 자료 시맨틱 검색 임베딩
        await conn.execute(text(
            "ALTER TABLE reference_material ADD COLUMN IF NOT EXISTS embedding vector(1536)"
        ))
        # IDEA-02 character state
        await conn.execute(text(
            "ALTER TABLE character ADD COLUMN IF NOT EXISTS status_location VARCHAR"
        ))
        await conn.execute(text(
            "ALTER TABLE character ADD COLUMN IF NOT EXISTS status_condition VARCHAR"
        ))
        await conn.execute(text(
            "ALTER TABLE character ADD COLUMN IF NOT EXISTS status_notes TEXT"
        ))
        await conn.execute(text(
            "ALTER TABLE character ADD COLUMN IF NOT EXISTS status_updated_at TIMESTAMP"
        ))
        # IDEA-09 / IDEA-05 episode fields
        await conn.execute(text(
            "ALTER TABLE episode ADD COLUMN IF NOT EXISTS author_notes TEXT"
        ))
        await conn.execute(text(
            "ALTER TABLE episode ADD COLUMN IF NOT EXISTS force_ending_hook BOOLEAN"
        ))
        # IDEA-08 / 13 / 05 project fields
        await conn.execute(text(
            "ALTER TABLE project ADD COLUMN IF NOT EXISTS style_guide TEXT"
        ))
        await conn.execute(text(
            "ALTER TABLE project ADD COLUMN IF NOT EXISTS low_cost_mode BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE project ADD COLUMN IF NOT EXISTS force_ending_hook BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        
        # WritingKnowHow 테이블 마이그레이션 (pgvector 지원)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS writing_know_how (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
                episode_id INTEGER REFERENCES episode(id) ON DELETE SET NULL,
                category VARCHAR(50) NOT NULL DEFAULT 'general',
                context_trigger VARCHAR(500) NOT NULL,
                problem_identified TEXT NOT NULL,
                lesson_learned TEXT NOT NULL,
                embedding vector(1536),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW())
            );
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_writing_know_how_project ON writing_know_how(project_id)"
        ))


# 모듈 로드 시 1회 생성 (요청마다 sessionmaker 재생성 방지)
async_session_factory = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


# FastAPI 비동기 세션 주입용 의존성(Dependency) 함수
async def get_async_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
        
async def close_db():
    await async_engine.dispose()


from psycopg_pool import AsyncConnectionPool
from typing import Optional

# psycopg 비동기 커넥션 풀 (LangGraph PostgresSaver 연동용)
psycopg_db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
connection_pool: Optional[AsyncConnectionPool] = None

def get_connection_pool() -> AsyncConnectionPool:
    global connection_pool
    if connection_pool is None:
        connection_pool = AsyncConnectionPool(
            conninfo=psycopg_db_url,
            kwargs={"autocommit": True},
            open=False,
            min_size=1,
            max_size=10
        )
    return connection_pool

