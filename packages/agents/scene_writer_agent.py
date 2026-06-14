from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import join_fields
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import SearchScope, get_agent_search_scope, load_repository_context, load_scoped_documents
from packages.schemas.agent_schemas import SceneWriterInput, SceneWriterOutput
from my_agent.domain import DraftKind
from my_agent.schemas import DraftCreate


@dataclass(slots=True)
class SceneWriterAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    search_scope: SearchScope | None = None
    embedder: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()
        self.search_scope = self.search_scope or get_agent_search_scope("scene_writer")

    def run(self, payload: SceneWriterInput) -> SceneWriterOutput:
        repository_context = load_repository_context(self.repository, payload.novel_id, self.search_scope)
        memory_documents = load_scoped_documents(self.memory_store, payload.novel_id, self.search_scope)
        draft_text = self._build_draft_text(payload)
        carryover_notes = self._build_carryover_notes(payload, repository_context)
        saved = self.repository.create_draft(
            DraftCreate(
                novel_id=payload.novel_id,
                kind=DraftKind.EPISODE_DRAFT,
                source_entity_type="episode",
                source_entity_id=payload.episode_card.episode_id,
                title=payload.episode_card.title_working,
                content=draft_text,
            )
        )

        return SceneWriterOutput(
            draft_text=draft_text,
            draft_title=payload.episode_card.title_working,
            ending_hook=payload.episode_card.cliffhanger,
            carryover_notes=carryover_notes,
            assumptions=["draft_text_derived_from_scene_beats"],
            retrieved_memory_document_ids=[getattr(document, "id", "") for document in memory_documents],
            approval_score=0.95,
            critical_issues=[],
        )

    def _build_draft_text(self, payload: SceneWriterInput) -> str:
        sections = [f"# {payload.episode_card.title_working}", ""]
        sections.append(payload.episode_card.hook_opening)
        for beat in payload.scene_beats:
            sections.extend(
                [
                    "",
                    f"## 장면 {beat.scene_order}",
                    f"목표: {beat.objective}",
                    f"갈등: {beat.conflict}",
                    f"결과: {beat.outcome}",
                    f"감정 변화: {beat.emotion_shift}",
                ]
            )
        sections.extend(["", f"화말 훅: {payload.episode_card.cliffhanger}"])
        return "\n".join(sections)

    def _build_carryover_notes(self, payload: SceneWriterInput, repository_context: dict[str, list[dict[str, object]]]) -> list[str]:
        notes = [f"scene_count={len(payload.scene_beats)}"]
        if repository_context.get("scene_beats"):
            notes.append("previous_scene_beats_available")
        if payload.style_rules:
            notes.append("style_rules_reflected")
        return notes
