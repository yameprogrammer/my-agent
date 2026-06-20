from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import (
    ALL_MODELS,
    ArcModel,
    ConceptModel,
    CharacterModel,
    DraftModel,
    EpisodeModel,
    EpisodePlanModel,
    MemoryDocumentModel,
    NovelModel,
    ThemeModel,
    SceneBeatModel,
    WorldRuleModel,
    SceneModel,
    ThreadModel,
    ValidationModel,
    GenerationRunModel,
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
    EpisodePlanCreate,
    EpisodePlanRead,
    MemoryDocumentCreate,
    MemoryDocumentRead,
    NovelCreate,
    NovelRead,
    SceneBeatCreate,
    SceneBeatRead,
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

    def create_concept(self, novel_id: str, title: str, summary: str, score: float | None = None, selected: bool = False) -> dict[str, object]:
        with session_scope(self.session_factory) as session:
            row = ConceptModel(
                id=str(uuid4()),
                novel_id=novel_id,
                title=title,
                summary=summary,
                score=score,
                status=RecordStatus.APPROVED.value if selected else RecordStatus.CREATED.value,
            )
            session.add(row)
            session.flush()
            return self._row_to_dict(row)

    def list_concepts(self, novel_id: str) -> list[dict[str, object]]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(ConceptModel).where(ConceptModel.novel_id == novel_id).order_by(ConceptModel.title)).scalars().all()
            return [self._row_to_dict(row) for row in rows]

    def create_theme(self, novel_id: str, name: str, description: str) -> dict[str, object]:
        with session_scope(self.session_factory) as session:
            row = ThemeModel(
                id=str(uuid4()),
                novel_id=novel_id,
                name=name,
                description=description,
            )
            session.add(row)
            session.flush()
            return self._row_to_dict(row)

    def list_themes(self, novel_id: str) -> list[dict[str, object]]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(ThemeModel).where(ThemeModel.novel_id == novel_id).order_by(ThemeModel.name)).scalars().all()
            return [self._row_to_dict(row) for row in rows]

    def create_world_rule(self, novel_id: str, rule_key: str, rule_value: str, revision_id: str | None = None) -> dict[str, object]:
        with session_scope(self.session_factory) as session:
            row = WorldRuleModel(
                id=str(uuid4()),
                novel_id=novel_id,
                rule_key=rule_key,
                rule_value=rule_value,
                revision_id=revision_id or str(uuid4()),
            )
            session.add(row)
            session.flush()
            return self._row_to_dict(row)

    def list_world_rules(self, novel_id: str) -> list[dict[str, object]]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(WorldRuleModel).where(WorldRuleModel.novel_id == novel_id).order_by(WorldRuleModel.rule_key)).scalars().all()
            return [self._row_to_dict(row) for row in rows]

    def list_characters(self, novel_id: str) -> list[CharacterRead]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(CharacterModel).where(CharacterModel.novel_id == novel_id).order_by(CharacterModel.name)).scalars().all()
            return [self._to_character_read(row) for row in rows]

    def list_arcs(self, novel_id: str) -> list[ArcRead]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(ArcModel).where(ArcModel.novel_id == novel_id).order_by(ArcModel.order_index)
            ).scalars().all()
            return [self._to_arc_read(row) for row in rows]

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

    def list_episodes(self, novel_id: str) -> list[EpisodeRead]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(EpisodeModel).where(EpisodeModel.novel_id == novel_id).order_by(EpisodeModel.episode_number)).scalars().all()
            return [self._to_episode_read(row) for row in rows]

    def create_episode_plan(self, payload: EpisodePlanCreate) -> dict[str, object]:
        with session_scope(self.session_factory) as session:
            row = EpisodePlanModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                episode_id=payload.episode_id,
                plan_json=payload.model_dump(),
                status=RecordStatus.APPROVED.value,
            )
            session.add(row)
            session.flush()
            return self._row_to_dict(row)

    def list_episode_plans(self, novel_id: str) -> list[dict[str, object]]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(EpisodePlanModel).where(EpisodePlanModel.novel_id == novel_id).order_by(EpisodePlanModel.id)).scalars().all()
            return [self._row_to_dict(row) for row in rows]

    def create_scene_beat(self, payload: SceneBeatCreate) -> dict[str, object]:
        with session_scope(self.session_factory) as session:
            row = SceneBeatModel(
                id=str(uuid4()),
                novel_id=payload.novel_id,
                episode_id=payload.episode_id,
                scene_order=payload.scene_order,
                objective=payload.objective,
                conflict=payload.conflict,
                outcome=payload.outcome,
                emotion_shift=payload.emotion_shift,
                participants_json=payload.participants_json,
                thread_ops_json=payload.thread_ops_json,
            )
            session.add(row)
            session.flush()
            return self._row_to_dict(row)

    def list_scene_beats(self, novel_id: str) -> list[dict[str, object]]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(SceneBeatModel).where(SceneBeatModel.novel_id == novel_id).order_by(SceneBeatModel.scene_order)).scalars().all()
            return [self._row_to_dict(row) for row in rows]

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

    def list_drafts(self, novel_id: str, kind: DraftKind | None = None) -> list[DraftRead]:
        with session_scope(self.session_factory) as session:
            query = select(DraftModel).where(DraftModel.novel_id == novel_id)
            if kind is not None:
                query = query.where(DraftModel.kind == kind.value)
            rows = session.execute(query.order_by(DraftModel.created_at.desc())).scalars().all()
            return [self._to_draft_read(row) for row in rows]

    def get_latest_draft(self, novel_id: str, kind: DraftKind | None = None) -> DraftRead | None:
        """Return the most recently created draft for the novel (optionally filtered by kind)."""
        drafts = self.list_drafts(novel_id, kind=kind)
        return drafts[0] if drafts else None

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

    def update_draft_content(self, draft_id: str, content: str) -> bool:
        """Update the content of an existing draft. Returns True if updated."""
        with session_scope(self.session_factory) as session:
            row = session.execute(
                select(DraftModel).where(DraftModel.id == draft_id)
            ).scalar_one_or_none()
            if row:
                row.content = content
                return True
            return False

    def create_validation(
        self,
        novel_id: str,
        target_entity_type: str,
        validation_type: str,
        issues: list[str],
        severity: str,
        blocking_decision: bool,
        score: float | None = None,
        target_entity_id: str | None = None,
        suggested_fix: str = "",
    ) -> dict[str, object]:
        with session_scope(self.session_factory) as session:
            row = ValidationModel(
                id=str(uuid4()),
                novel_id=novel_id,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
                validation_type=validation_type,
                status=RecordStatus.REJECTED.value if blocking_decision else RecordStatus.APPROVED.value,
                score=score,
                issues_json={
                    "issues": issues,
                    "severity": severity,
                    "blocking_decision": blocking_decision,
                    "suggested_fix": suggested_fix,
                },
            )
            session.add(row)
            session.flush()
            return self._row_to_dict(row)

    def update_validation_status(self, validation_id: str, status: RecordStatus) -> bool:
        """Update status of a validation record. Returns True if found and updated."""
        with session_scope(self.session_factory) as session:
            row = session.execute(
                select(ValidationModel).where(ValidationModel.id == validation_id)
            ).scalar_one_or_none()
            if row:
                row.status = status.value
                return True
            return False

    def list_validations(self, novel_id: str, validation_type: str | None = None) -> list[dict[str, object]]:
        with session_scope(self.session_factory) as session:
            query = select(ValidationModel).where(ValidationModel.novel_id == novel_id)
            if validation_type is not None:
                query = query.where(ValidationModel.validation_type == validation_type)
            rows = session.execute(query.order_by(ValidationModel.id)).scalars().all()
            return [self._row_to_dict(row) for row in rows]

    def list_generation_runs(self, novel_id: str, limit: int = 10) -> list[dict[str, object]]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(GenerationRunModel)
                .where(GenerationRunModel.novel_id == novel_id)
                .order_by(GenerationRunModel.created_at.desc())
                .limit(limit)
            ).scalars().all()
            return [self._row_to_dict(row) for row in rows]

    def get_project_summary(self, novel_id: str) -> dict[str, object]:
        """Return a summary of key stats for a novel/project for dashboard use."""
        with session_scope(self.session_factory) as session:
            arc_count = (
                session.execute(
                    select(func.count(ArcModel.id)).where(ArcModel.novel_id == novel_id)
                ).scalar_one()
                or 0
            )
            episode_count = (
                session.execute(
                    select(func.count(EpisodeModel.id)).where(EpisodeModel.novel_id == novel_id)
                ).scalar_one()
                or 0
            )
            draft_count = (
                session.execute(
                    select(func.count(DraftModel.id)).where(DraftModel.novel_id == novel_id)
                ).scalar_one()
                or 0
            )
            pending_validation_count = (
                session.execute(
                    select(func.count(ValidationModel.id))
                    .where(ValidationModel.novel_id == novel_id)
                    .where(
                        ~ValidationModel.status.in_(
                            [RecordStatus.APPROVED.value, RecordStatus.REJECTED.value]
                        )
                    )
                ).scalar_one()
                or 0
            )
            latest_draft = self.get_latest_draft(novel_id)  # uses list_drafts internally

        return {
            "novel_id": novel_id,
            "arc_count": arc_count,
            "episode_count": episode_count,
            "draft_count": draft_count,
            "pending_validation_count": pending_validation_count,
            "has_latest_draft": latest_draft is not None,
            "latest_draft_kind": latest_draft.kind.value if latest_draft else None,
            "latest_draft_title": latest_draft.title if latest_draft else None,
        }

    def archive_novel(self, novel_id: str) -> bool:
        """Soft-archive a novel by setting its status to ARCHIVED. Returns True if updated."""
        with session_scope(self.session_factory) as session:
            row = session.execute(
                select(NovelModel).where(NovelModel.novel_id == novel_id)
            ).scalar_one_or_none()
            if row:
                row.status = NovelStatus.ARCHIVED.value
                return True
            return False

    def upsert_memory_document(self, payload: MemoryDocumentCreate) -> MemoryDocumentRead:
        from .memory import MemoryStore

        return MemoryStore(self.engine.url.database).upsert_memory_document(payload)

    @staticmethod
    def _row_to_dict(row: object) -> dict[str, object]:
        return {key: getattr(row, key) for key in row.__mapper__.columns.keys()}

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

    @staticmethod
    def _row_to_readable_plan(row: EpisodePlanModel) -> EpisodePlanRead:
        return EpisodePlanRead(
            id=row.id,
            novel_id=row.novel_id,
            episode_id=row.episode_id,
            plan_json=row.plan_json or {},
            status=RecordStatus(row.status),
        )

    @staticmethod
    def _row_to_readable_scene_beat(row: SceneBeatModel) -> SceneBeatRead:
        return SceneBeatRead(
            id=row.id,
            novel_id=row.novel_id,
            episode_id=row.episode_id,
            scene_order=row.scene_order,
            objective=row.objective,
            conflict=row.conflict,
            outcome=row.outcome,
            emotion_shift=row.emotion_shift,
            participants_json=row.participants_json or {},
            thread_ops_json=row.thread_ops_json or {},
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
