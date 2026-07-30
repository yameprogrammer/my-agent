from sqlmodel import SQLModel, Field, Relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer
from datetime import datetime
from typing import Optional, List

# SQLModel 관계 클래스의 Type Hinting 순환 참조 방지를 위해 forward reference 사용

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    email: Optional[str] = Field(default=None, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # 관리자 승인 전까지 비활성 상태로 유지
    is_active: bool = Field(default=False, nullable=False)
    # 관리자 계정 여부 (승인 권한 보유)
    is_admin: bool = Field(default=False, nullable=False)
    
    # 거절 이력 관리 (신규 추가)
    rejected_at: Optional[datetime] = Field(default=None, nullable=True)  # 거절된 시각, None이면 미거절
    
    projects: List["Project"] = Relationship(back_populates="user")


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    title: str = Field(nullable=False)
    synopsis: Optional[str] = Field(default=None)
    
    # AI 집필에 사용될 LLM 설정 (사용자가 직접 선택 가능)
    llm_provider: str = Field(default="openai", nullable=False) # "openai" | "google" | "anthropic" | "nvidia" | "ollama" | "custom_openai"
    llm_model: str = Field(default="gpt-4o-mini", nullable=False)
    api_key_override: Optional[str] = Field(default=None, nullable=True) # 유저가 개별 키를 쓸 경우 저장
    
    # 1) Plotter Agent (기획) 오버라이드 설정
    plotter_provider: Optional[str] = Field(default=None, nullable=True)
    plotter_model: Optional[str] = Field(default=None, nullable=True)
    plotter_api_key: Optional[str] = Field(default=None, nullable=True)

    # 2) Writer Agent (집필) 오버라이드 설정
    writer_provider: Optional[str] = Field(default=None, nullable=True)
    writer_model: Optional[str] = Field(default=None, nullable=True)
    writer_api_key: Optional[str] = Field(default=None, nullable=True)

    # 3) Judge Agent (모순 감지) 오버라이드 설정
    judge_provider: Optional[str] = Field(default=None, nullable=True)
    judge_model: Optional[str] = Field(default=None, nullable=True)
    judge_api_key: Optional[str] = Field(default=None, nullable=True)

    # 4) Editor Agent (교정/윤문) 오버라이드 설정
    editor_provider: Optional[str] = Field(default=None, nullable=True)
    editor_model: Optional[str] = Field(default=None, nullable=True)
    editor_api_key: Optional[str] = Field(default=None, nullable=True)

    # 5) Reviewer Agent (종합 평가) 오버라이드 설정
    reviewer_provider: Optional[str] = Field(default=None, nullable=True)
    reviewer_model: Optional[str] = Field(default=None, nullable=True)
    reviewer_api_key: Optional[str] = Field(default=None, nullable=True)

    # IDEA-08: 문체 샘플 / 스타일 가이드 (Writer·Editor 주입)
    style_guide: Optional[str] = Field(default=None)
    # IDEA-13: 저비용 모드 — Plotter/Judge/Editor 소형 모델 프리셋
    low_cost_mode: bool = Field(default=False, nullable=False)
    # IDEA-05: 프로젝트 기본 말미 훅 강제
    force_ending_hook: bool = Field(default=False, nullable=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="projects")
    world_settings: List["WorldSetting"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    characters: List["Character"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    episodes: List["Episode"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    reference_materials: List["ReferenceMaterial"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    plot_threads: List["PlotThread"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    usage_logs: List["AgentUsageLog"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    share_links: List["ProjectShareLink"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    writing_know_hows: List["WritingKnowHow"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )



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
    # IDEA-02: 캐릭터 상태 스냅샷 (위치·관계·부상 등)
    status_location: Optional[str] = Field(default=None)
    status_condition: Optional[str] = Field(default=None)  # healthy | injured | missing | dead | unknown
    status_notes: Optional[str] = Field(default=None)  # 관계·아크 진행 free text
    status_updated_at: Optional[datetime] = Field(default=None)
    
    project: Project = Relationship(back_populates="characters")


class Episode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False)
    episode_number: int = Field(nullable=False) # 1화, 2화 ...
    title: str = Field(nullable=False)
    outline: Optional[str] = Field(default=None)
    # IMP-07: 승인 시 자동 요약 — 다음 회차 Plotter/Writer 연속성 주입
    summary: Optional[str] = Field(default=None)
    # IDEA-09: 작가 메모 (outline 과 별도, RAG/Plotter 주입)
    author_notes: Optional[str] = Field(default=None)
    # IDEA-05: 회차 단위 말미 훅 강제 (None=프로젝트 기본 따름)
    force_ending_hook: Optional[bool] = Field(default=None)
    rag_threshold: float = Field(default=0.5, nullable=False)
    rag_limit: int = Field(default=5, nullable=False)
    force_reference_ids: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    project: Project = Relationship(back_populates="episodes")
    contents: List["Content"] = Relationship(
        back_populates="episode", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Content(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # 회차 삭제 시 DB 레벨에서도 본문이 함께 제거되도록 CASCADE
    episode_id: int = Field(
        sa_column=Column(Integer, ForeignKey("episode.id", ondelete="CASCADE"), nullable=False)
    )
    # self-referencing relationship for version control tree structure
    parent_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("content.id", ondelete="SET NULL"), nullable=True)
    )
    
    content_text: str = Field(nullable=False)
    author_type: str = Field(default="ai", nullable=False)  # "ai" | "user" | "hybrid" (H1 human edit)
    version_tag: str = Field(default="v1.0", nullable=False) # "v1.0" | "v1.1-feedback-applied"
    is_approved: bool = Field(default=False, nullable=False) # 이 버전을 최종 승인(선택)했는지 여부
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    episode: Episode = Relationship(back_populates="contents")


class ReferenceMaterial(SQLModel, table=True):
    __tablename__ = "reference_material"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False)
    
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    category: str = Field(default="etc", nullable=False)  # "history" | "science" | "medical" | "law" | "etc"
    source_type: str = Field(default="web", nullable=False)  # "web" | "academic" | "sns" | "community"
    source_url: Optional[str] = Field(default=None, nullable=True)

    # IMP-11: 시맨틱 검색용 1536-d 임베딩 (WorldSetting 과 동일 차원)
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=True)
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="reference_materials")


class PlotThread(SQLModel, table=True):
    """IDEA-03: 복선 / 미해결 실타래 레지스트리."""
    __tablename__ = "plot_thread"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False)
    title: str = Field(nullable=False)
    description: str = Field(default="", nullable=False)
    status: str = Field(default="open", nullable=False)  # open | planted | resolved | dropped
    # 회차 삭제 시 복선 레코드는 유지하고 회차 링크만 끊음
    planted_episode_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("episode.id", ondelete="SET NULL"), nullable=True),
    )
    target_episode_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("episode.id", ondelete="SET NULL"), nullable=True),
    )
    resolved_episode_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("episode.id", ondelete="SET NULL"), nullable=True),
    )
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="plot_threads")


class AgentUsageLog(SQLModel, table=True):
    """IDEA-11/12: 에이전트 호출 관측 (프롬프트 전문 미저장 — 해시·대략 토큰만)."""
    __tablename__ = "agent_usage_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    # 회차 삭제 시 사용 로그는 보존 (episode_id만 NULL)
    episode_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("episode.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    agent_role: str = Field(nullable=False, index=True)  # plotter | writer | judge | ...
    model_name: Optional[str] = Field(default=None)
    provider: Optional[str] = Field(default=None)
    latency_ms: int = Field(default=0, nullable=False)
    prompt_hash: Optional[str] = Field(default=None)
    input_chars: int = Field(default=0, nullable=False)
    output_chars: int = Field(default=0, nullable=False)
    est_input_tokens: int = Field(default=0, nullable=False)
    est_output_tokens: int = Field(default=0, nullable=False)
    success: bool = Field(default=True, nullable=False)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    project: Project = Relationship(back_populates="usage_logs")


class ProjectShareLink(SQLModel, table=True):
    """IDEA-18: 읽기 전용 공유 티켓."""
    __tablename__ = "project_share_link"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    token: str = Field(index=True, unique=True, nullable=False)
    label: Optional[str] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    is_revoked: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="share_links")


class WritingKnowHow(SQLModel, table=True):
    """지속 학습 엔진을 통해 추출된 세부 집필 노하우 및 피드백 극복 사례."""
    __tablename__ = "writing_know_how"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    episode_id: Optional[int] = Field(
        sa_column=Column(Integer, ForeignKey("episode.id", ondelete="SET NULL"), nullable=True)
    )
    
    category: str = Field(default="general", nullable=False) # general | style | dialogue | action | logic | lore
    context_trigger: str = Field(nullable=False) # RAG 쿼리 및 매칭을 위한 상황 키워드 (e.g. "검술 전투 묘사")
    problem_identified: str = Field(nullable=False) # 기존에 발생했던 문제점
    lesson_learned: str = Field(nullable=False) # 해결책 및 향후 준수 지침
    
    # 1536차원 임베딩 컬럼 (pgvector)
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=True)
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    project: Project = Relationship(back_populates="writing_know_hows")

