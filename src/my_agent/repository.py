from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import (
    ALL_MODELS,
    ArcModel,
    CharacterModel,
    DraftModel,
    EpisodeModel,
    MemoryDocumentModel,
    NovelModel,
    SceneModel,
    ThreadModel,
    create_engine_and_session,
    create_schema,
    session_scope,
)
from .domain import Arc, ArcLevel, Character, DraftKind, Episode, Novel, NovelStatus, RecordStatus, Scene, Thread, ThreadStatus
from .schemas import (
    ArcCreate,
    ArcRead,
    CharacterCreate,
    CharacterRead,
    DraftCreate,
    DraftRead,
    EpisodeCreate,
    EpisodeRead,
    MemoryDocumentCreate,
    MemoryDocumentRead,
    NovelCreate,
    NovelRead,
    SceneCreate,
    SceneRead,
    ThreadCreate,
    ThreadRead,
)


class NovelRepository:
    def __init__(self, db_path: str | Path):
        self.engine, self.session_factory = create_engine_and_session(db_path)
        create_schema(self.engine)

    def create_novel(self, payload: NovelCreate) -> NovelRead:
        with session_scope(self.session_factory) as session:
            row = NovelModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                title=payload.title,
                genre=payload.genre,
                target_format=payload.target_format,
                status=NovelStatus.DRAFT.value,
            )
            session.add(row)
            session.flush()
            return self._to_novel_read(row)

    def get_novel(self, novel_id: str) -> NovelRead | None:
        with session_scope(self.session_factory) as session:
            row = session.execute(select(NovelModel).where(NovelModel.novel_id == novel_id)).scalar_one_or_none()
            return None if row is None else self._to_novel_read(row)

    def list_novels(self) -> list[NovelRead]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(NovelModel).order_by(NovelModel.title)).scalars().all()
            return [self._to_novel_read(row) for row in rows]

    def create_character(self, payload: CharacterCreate) -> CharacterRead:
        with session_scope(self.session_factory) as session:
            row = CharacterModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                name=payload.name,
                role=payload.role,
                revision_id=str(uuid4()),
                metadata_json=payload.metadata,
            )
            session.add(row)
            session.flush()
            return self._to_character_read(row)

    def list_characters(self, novel_id: str) -> list[CharacterRead]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(CharacterModel).where(CharacterModel.novel_id == novel_id).order_by(CharacterModel.name)).scalars().all()
            return [self._to_character_read(row) for row in rows]

    def create_arc(self, payload: ArcCreate) -> ArcRead:
        with session_scope(self.session_factory) as session:
            row = ArcModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                title=payload.title,
                arc_level=payload.arc_level.value,
                order_index=payload.order_index,
                status=RecordStatus.CREATED.value,
                revision_id=str(uuid4()),
            )
            session.add(row)
            session.flush()
            return self._to_arc_read(row)

    def create_episode(self, payload: EpisodeCreate) -> EpisodeRead:
        with session_scope(self.session_factory) as session:
            row = EpisodeModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                episode_number=payload.episode_number,
                title_working=payload.title_working,
                arc_id=payload.arc_id,
                pov_character_id=payload.pov_character_id,
                status=RecordStatus.CREATED.value,
            )
            session.add(row)
            session.flush()
            return self._to_episode_read(row)

    def create_scene(self, payload: SceneCreate) -> SceneRead:
        with session_scope(self.session_factory) as session:
            row = SceneModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                episode_id=payload.episode_id,
                scene_order=payload.scene_order,
                objective=payload.objective,
                conflict=payload.conflict,
                outcome=payload.outcome,
            )
            session.add(row)
            session.flush()
            return self._to_scene_read(row)

    def create_thread(self, payload: ThreadCreate) -> ThreadRead:
        with session_scope(self.session_factory) as session:
            row = ThreadModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                thread_type=payload.thread_type,
                planted_episode_id=payload.planted_episode_id,
                latest_episode_id=payload.latest_episode_id,
                planned_payoff_episode_id=payload.planned_payoff_episode_id,
                status=payload.status.value,
                importance=payload.importance,
                revision_id=str(uuid4()),
            )
            session.add(row)
            session.flush()
            return self._to_thread_read(row)

    def create_draft(self, payload: DraftCreate) -> DraftRead:
        with session_scope(self.session_factory) as session:
            row = DraftModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                kind=payload.kind.value,
                source_entity_type=payload.source_entity_type,
                source_entity_id=payload.source_entity_id,
                title=payload.title,
                content=payload.content,
                status=payload.status.value,
            )
            session.add(row)
            session.flush()
            return self._to_draft_read(row)

    def upsert_memory_document(self, payload: MemoryDocumentCreate) -> MemoryDocumentRead:
        from .memory import MemoryStore

        return MemoryStore(self.engine.url.database).upsert_memory_document(payload)

    def _to_novel_read(self, row: NovelModel) -> NovelRead:
        return NovelRead(
            novel_id=row.novel_id,
            title=row.title,
            genre=row.genre,
            target_format=row.target_format,
            status=NovelStatus(row.status),
            current_revision_id=row.current_revision_id,
        )

    def _to_character_read(self, row: CharacterModel) -> CharacterRead:
        return CharacterRead(
            id=row.id,
            novel_id=row.novel_id,
            name=row.name,
            role=row.role,
            revision_id=row.revision_id,
            metadata=row.metadata_json or {},
        )

    def _to_arc_read(self, row: ArcModel) -> ArcRead:
        return ArcRead(
            id=row.id,
            novel_id=row.novel_id,
            title=row.title,
            arc_level=ArcLevel(row.arc_level),
            order_index=row.order_index,
            status=RecordStatus(row.status),
            revision_id=row.revision_id,
        )

    def _to_episode_read(self, row: EpisodeModel) -> EpisodeRead:
        return EpisodeRead(
            id=row.id,
            novel_id=row.novel_id,
            episode_number=row.episode_number,
            title_working=row.title_working,
            arc_id=row.arc_id,
            pov_character_id=row.pov_character_id,
            status=RecordStatus(row.status),
            approved_revision_id=row.approved_revision_id,
        )

    def _to_scene_read(self, row: SceneModel) -> SceneRead:
        return SceneRead(
            id=row.id,
            novel_id=row.novel_id,
            episode_id=row.episode_id,
            scene_order=row.scene_order,
            objective=row.objective,
            conflict=row.conflict,
            outcome=row.outcome,
        )

    def _to_thread_read(self, row: ThreadModel) -> ThreadRead:
        return ThreadRead(
            id=row.id,
            novel_id=row.novel_id,
            thread_type=row.thread_type,
            planted_episode_id=row.planted_episode_id,
            latest_episode_id=row.latest_episode_id,
            planned_payoff_episode_id=row.planned_payoff_episode_id,
            status=ThreadStatus(row.status),
            importance=row.importance,
            revision_id=row.revision_id,
        )

    def _to_draft_read(self, row: DraftModel) -> DraftRead:
        return DraftRead(
            id=row.id,
            novel_id=row.novel_id,
            kind=DraftKind(row.kind),
            source_entity_type=row.source_entity_type,
            source_entity_id=row.source_entity_id,
            title=row.title,
            content=row.content,
            status=RecordStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
