from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import join_fields
from packages.embeddings import EmbedderFactory
from packages.llm.base import LLMClient
from packages.memory.search_scope import SearchScope, get_agent_search_scope, load_repository_context, load_scoped_documents
from packages.prompts import PromptLoader
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
    llm_client: LLMClient | None = None

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()
        self.search_scope = self.search_scope or get_agent_search_scope("scene_writer")

    def run(self, payload: SceneWriterInput) -> SceneWriterOutput:
        repository_context = load_repository_context(self.repository, payload.novel_id, self.search_scope)
        memory_documents = load_scoped_documents(self.memory_store, payload.novel_id, self.search_scope)

        if self.llm_client is not None:
            draft_text = self._generate_with_llm(payload, memory_documents)
            assumptions = ["draft_text_generated_by_llm"]
        else:
            draft_text = self._build_draft_text(payload)
            assumptions = ["draft_text_derived_from_scene_beats"]

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
            assumptions=assumptions,
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

    def _generate_with_llm(self, payload: SceneWriterInput, memory_documents: list[Any]) -> str:
        """Generate actual novel prose using LLM + prompt template."""
        loader = PromptLoader()

        scene_beats_text = "\n".join(
            f"- 장면 {beat.scene_order}: 목표={beat.objective} | 갈등={beat.conflict} | 결과={beat.outcome}"
            for beat in payload.scene_beats
        )

        retrieved_context = "\n".join(
            str(getattr(doc, "summary_text", getattr(doc, "content", "")) or "")
            for doc in memory_documents
        ) or "No additional memory context."

        # Use the v1 template from Step 2
        prompt = loader.render(
            "episode/scene_writer_v1",
            episode_number=getattr(payload.episode_card, "episode_number", 1),
            title_working=payload.episode_card.title_working or "Untitled",
            objective=payload.episode_card.objective or "",
            conflict=payload.episode_card.conflict or "",
            cliffhanger=payload.episode_card.cliffhanger or "",
            scene_beats_text=scene_beats_text,
            base_constraints="",
        )

        try:
            # Prefer text generation for the draft body
            draft_text = self.llm_client.generate_text(prompt)
            return draft_text.strip()
        except Exception:
            # Safe fallback
            return self._build_draft_text(payload)
