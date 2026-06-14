from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, join_fields
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import SearchScope, get_agent_search_scope, load_repository_context, load_scoped_documents
from packages.schemas.agent_schemas import EpisodeDetailInput, EpisodeDetailOutput, SceneBeatSpec
from my_agent.schemas import SceneBeatCreate


@dataclass(slots=True)
class EpisodeDetailAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    search_scope: SearchScope | None = None
    embedder: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()
        self.search_scope = self.search_scope or get_agent_search_scope("episode_detail")

    def run(self, payload: EpisodeDetailInput) -> EpisodeDetailOutput:
        repository_context = load_repository_context(self.repository, payload.novel_id, self.search_scope)
        memory_documents = load_scoped_documents(self.memory_store, payload.novel_id, self.search_scope)
        scene_count = max(3, min(6, payload.episode_card.scene_count))
        episode_embedding = self.embedder.embed_text(
            join_fields(
                payload.episode_card.title_working,
                payload.episode_card.objective,
                payload.episode_card.conflict,
                payload.episode_card.cliffhanger,
                " ".join(payload.open_threads),
            )
        )

        scene_beats: list[SceneBeatSpec] = []
        scene_beat_ids: list[str] = []
        for scene_order in range(1, scene_count + 1):
            beat = self._build_scene_beat(payload, scene_order)
            saved = self.repository.create_scene_beat(
                SceneBeatCreate(
                    novel_id=payload.novel_id,
                    episode_id=payload.episode_card.episode_id,
                    scene_order=beat.scene_order,
                    objective=beat.objective,
                    conflict=beat.conflict,
                    outcome=beat.outcome,
                    emotion_shift=beat.emotion_shift,
                    participants_json={"participants": beat.participants},
                    thread_ops_json={"thread_ops": beat.thread_ops},
                )
            )
            scene_beats.append(beat)
            scene_beat_ids.append(saved["id"])

        score = 0.93 if len(scene_beats) >= 3 else 0.88
        score = min(0.98, score + cosine_similarity(episode_embedding, self.embedder.embed_text(payload.episode_card.theme)) * 0.01)

        return EpisodeDetailOutput(
            scene_beats=scene_beats,
            assumptions=self._build_assumptions(payload, repository_context),
            retrieved_memory_document_ids=[getattr(document, "id", "") for document in memory_documents],
            approval_score=score,
            critical_issues=[] if len(scene_beats) >= 3 else ["scene_count_too_low"],
        )

    def _build_scene_beat(self, payload: EpisodeDetailInput, scene_order: int) -> SceneBeatSpec:
        participant = payload.episode_card.pov_hint or "주인공"
        return SceneBeatSpec(
            scene_order=scene_order,
            objective=f"{payload.episode_card.objective} - {scene_order}단계",
            conflict=f"{payload.episode_card.conflict}가 {scene_order}번째 장면에서 격화된다.",
            outcome=f"{payload.episode_card.outcome}의 일부가 드러난다.",
            emotion_shift=f"긴장도 {scene_order}단계 상승",
            participants=[participant, payload.episode_card.arc_title],
            thread_ops=[f"advance_arc_{payload.episode_card.arc_number}", f"maintain_hook_{scene_order}"],
        )

    def _build_assumptions(self, payload: EpisodeDetailInput, repository_context: dict[str, list[dict[str, object]]]) -> list[str]:
        assumptions: list[str] = []
        if repository_context.get("episode_plans"):
            assumptions.append("episode_plan_context_available")
        if payload.open_threads:
            assumptions.append("open_threads_used_as_continuity_inputs")
        if payload.style_rules:
            assumptions.append("style_rules_applied_to_scene_flow")
        return assumptions
