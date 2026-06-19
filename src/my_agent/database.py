from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, Text, create_engine, event, func, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import DEFAULT_EMBEDDING_MODEL, DEFAULT_SQLITE_PATH
from .domain import ArcLevel, DraftKind, NovelStatus, RecordStatus, ThreadStatus

metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


class NovelModel(Base):
    __tablename__ = "novels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(64), nullable=False, default="fantasy")
    target_format: Mapped[str] = mapped_column(String(64), nullable=False, default="webnovel")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=NovelStatus.DRAFT.value)
    current_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    characters: Mapped[list["CharacterModel"]] = relationship(back_populates="novel")
    arcs: Mapped[list["ArcModel"]] = relationship(back_populates="novel")
    episodes: Mapped[list["EpisodeModel"]] = relationship(back_populates="novel")


class CharacterModel(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), ForeignKey("novels.novel_id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    revision_id: Mapped[str] = mapped_column(String(36), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata_json", JSON, nullable=False, default=dict)

    novel: Mapped[NovelModel] = relationship(back_populates="characters")


class ArcModel(Base):
    __tablename__ = "arcs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), ForeignKey("novels.novel_id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    arc_level: Mapped[str] = mapped_column(String(16), nullable=False, default=ArcLevel.MAIN.value)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)
    revision_id: Mapped[str] = mapped_column(String(36), nullable=False)

    novel: Mapped[NovelModel] = relationship(back_populates="arcs")
    episodes: Mapped[list["EpisodeModel"]] = relationship(back_populates="arc")


class EpisodeModel(Base):
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), ForeignKey("novels.novel_id"), index=True, nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_working: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    arc_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("arcs.id"), nullable=True)
    pov_character_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("characters.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)
    approved_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    novel: Mapped[NovelModel] = relationship(back_populates="episodes")
    arc: Mapped[ArcModel | None] = relationship(back_populates="episodes")
    scenes: Mapped[list["SceneModel"]] = relationship(back_populates="episode")


class SceneModel(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    episode_id: Mapped[str] = mapped_column(String(36), ForeignKey("episodes.id"), nullable=False)
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    conflict: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")

    episode: Mapped[EpisodeModel] = relationship(back_populates="scenes")


class ThreadModel(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    thread_type: Mapped[str] = mapped_column(String(64), nullable=False)
    planted_episode_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latest_episode_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    planned_payoff_episode_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ThreadStatus.PLANTED.value)
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision_id: Mapped[str] = mapped_column(String(36), nullable=False)


class DraftModel(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)


class MemoryDocumentModel(Base):
    __tablename__ = "memory_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)


class ValidationModel(Base):
    __tablename__ = "validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    validation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    issues_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class GenerationRunModel(Base):
    __tablename__ = "generation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retrieved_memory_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, default="local")
    raw_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parsed_output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    validation_result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reviewer_decision: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)


class PromptLogModel(Base):
    __tablename__ = "prompt_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    prompt_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    variables_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ConceptModel(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)


class ThemeModel(Base):
    __tablename__ = "themes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class WorldRuleModel(Base):
    __tablename__ = "world_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_key: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_value: Mapped[str] = mapped_column(Text, nullable=False)
    revision_id: Mapped[str] = mapped_column(String(36), nullable=False)


class FactionModel(Base):
    __tablename__ = "factions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class LocationModel(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class CharacterStateModel(Base):
    __tablename__ = "character_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    character_id: Mapped[str] = mapped_column(String(36), ForeignKey("characters.id"), nullable=False)
    episode_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    state_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class TimelineEventModel(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    absolute_order: Mapped[int] = mapped_column(Integer, nullable=False)
    relative_time_label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    event_summary: Mapped[str] = mapped_column(Text, nullable=False)
    participants_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    consequences_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class EpisodePlanModel(Base):
    __tablename__ = "episode_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    episode_id: Mapped[str] = mapped_column(String(36), ForeignKey("episodes.id"), nullable=False)
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)


class SceneBeatModel(Base):
    __tablename__ = "scene_beats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    episode_id: Mapped[str] = mapped_column(String(36), ForeignKey("episodes.id"), nullable=False)
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    conflict: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")
    emotion_shift: Mapped[str] = mapped_column(Text, nullable=False, default="")
    participants_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    thread_ops_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SubArcModel(Base):
    __tablename__ = "sub_arcs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    arc_id: Mapped[str] = mapped_column(String(36), ForeignKey("arcs.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)


class NovelRevisionModel(Base):
    __tablename__ = "novel_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    revision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RecordStatus.CREATED.value)


ALL_MODELS = [
    NovelModel,
    NovelRevisionModel,
    ConceptModel,
    ThemeModel,
    WorldRuleModel,
    CharacterModel,
    CharacterStateModel,
    FactionModel,
    LocationModel,
    ArcModel,
    SubArcModel,
    EpisodeModel,
    EpisodePlanModel,
    SceneBeatModel,
    SceneModel,
    DraftModel,
    MemoryDocumentModel,
    ThreadModel,
    TimelineEventModel,
    ValidationModel,
    GenerationRunModel,
    PromptLogModel,
]


def create_engine_and_session(db_path: str | Path = DEFAULT_SQLITE_PATH) -> tuple[Engine, sessionmaker]:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    _enable_sqlite_foreign_keys(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine, session_factory


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _migrate_generation_run_timestamps(engine)
    _create_vector_table(engine)


def _migrate_generation_run_timestamps(engine: Engine) -> None:
    with engine.begin() as connection:
        table_exists = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='generation_runs'"
        ).fetchone()
        if table_exists is None:
            return
        columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(generation_runs)").fetchall()
        }
        if "created_at" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE generation_runs ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            )
        if "updated_at" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE generation_runs ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            )


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


def _create_vector_table(engine: Engine) -> None:
    with engine.begin() as connection:
        try:
            import sqlite_vec

            connection.connection.enable_load_extension(True)
            sqlite_vec.load(connection.connection)
            connection.connection.enable_load_extension(False)
            connection.exec_driver_sql(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                    embedding float[384],
                    novel_id TEXT,
                    doc_id TEXT
                )
                """
            )
        except Exception:
            return


@contextmanager
def session_scope(session_factory: sessionmaker) -> Iterator:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
