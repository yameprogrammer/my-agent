from sqlmodel import SQLModel, Field, Relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from datetime import datetime
from typing import Optional, List

# SQLModel 관계 클래스의 Type Hinting 순환 참조 방지를 위해 forward reference 사용

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    email: Optional[str] = Field(default=None, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    projects: List["Project"] = Relationship(back_populates="user")


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    title: str = Field(nullable=False)
    synopsis: Optional[str] = Field(default=None)
    
    # AI 집필에 사용될 LLM 설정 (사용자가 직접 선택 가능)
    llm_provider: str = Field(default="openai", nullable=False) # "openai" | "google" | "anthropic" | "ollama"
    llm_model: str = Field(default="gpt-4o-mini", nullable=False)
    api_key_override: Optional[str] = Field(default=None, nullable=True) # 유저가 개별 키를 쓸 경우 저장
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="projects")
    world_settings: List["WorldSetting"] = Relationship(back_populates="project")
    characters: List["Character"] = Relationship(back_populates="project")
    episodes: List["Episode"] = Relationship(back_populates="project")


class WorldSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False)
    keyword: str = Field(index=True, nullable=False)
    category: str = Field(nullable=False) # "lore" | "location" | "item" | "concept"
    description: str = Field(nullable=False)
    
    # 1536차원 OpenAI 임베딩 컬럼 (sa_column을 사용하여 pgvector 연동)
    # sa_column 내 Column 생성 시 Vector 타입 지정 필수
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=True)
    )
    
    project: Project = Relationship(back_populates="world_settings")


class Character(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False)
    name: str = Field(index=True, nullable=False)
    description: str = Field(nullable=False)
    importance: str = Field(default="minor", nullable=False) # "protagonist" | "deuteragonist" | "major" | "minor"
    
    project: Project = Relationship(back_populates="characters")


class Episode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False)
    episode_number: int = Field(nullable=False) # 1화, 2화 ...
    title: str = Field(nullable=False)
    outline: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    project: Project = Relationship(back_populates="episodes")
    contents: List["Content"] = Relationship(back_populates="episode")


class Content(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    episode_id: int = Field(foreign_key="episode.id", nullable=False)
    # self-referencing relationship for version control tree structure
    parent_id: Optional[int] = Field(default=None, foreign_key="content.id", nullable=True)
    
    content_text: str = Field(nullable=False)
    author_type: str = Field(default="ai", nullable=False) # "ai" | "user" | "hybrid"
    version_tag: str = Field(default="v1.0", nullable=False) # "v1.0" | "v1.1-feedback-applied"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    episode: Episode = Relationship(back_populates="contents")
