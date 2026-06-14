from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, join_fields
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import SearchScope, get_agent_search_scope, load_repository_context, load_scoped_documents
from packages.schemas.agent_schemas import EpisodeCard, EpisodeCycleInput, EpisodeCycleOutput
from my_agent.schemas import EpisodeCreate, EpisodePlanCreate


@dataclass(slots=True)
class EpisodeCycleAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    search_scope: SearchScope | None = None
    embedder: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()
        self.search_scope = self.search_scope or get_agent_search_scope("episode_cycle")

    def run(self, payload: EpisodeCycleInput) -> EpisodeCycleOutput:
        repository_context = load_repository_context(self.repository, payload.novel_id, self.search_scope)
        memory_documents = load_scoped_documents(self.memory_store, payload.novel_id, self.search_scope)
        if not payload.approved_arcs:
            return EpisodeCycleOutput(
                critical_issues=["approved_arcs_empty"],
                approval_score=0.0,
                retrieved_memory_document_ids=[getattr(document, "id", "") for document in memory_documents],
            )

        total_episodes = max(20, payload.target_episode_count)
        if total_episodes > 30:
            total_episodes = 30

        arc_context = join_fields(
            " ".join(arc.title for arc in payload.approved_arcs),
            " ".join(arc.objective for arc in payload.approved_arcs),
            " ".join(arc.payoff for arc in payload.approved_arcs),
            " ".join(item.get("name", "") for item in repository_context.get("episode_plans", [])),
        )
        arc_embedding = self.embedder.embed_text(arc_context or payload.novel_id)

        episode_cards: list[EpisodeCard] = []
        episode_ids: list[str] = []
        plan_ids: list[str] = []
        for episode_number in range(1, total_episodes + 1):
            arc = payload.approved_arcs[(episode_number - 1) % len(payload.approved_arcs)]
            card = self._build_episode_card(payload.novel_id, episode_number, arc)
            episode = self.repository.create_episode(
                EpisodeCreate(
                    novel_id=payload.novel_id,
                    episode_number=card.episode_number,
                    title_working=card.title_working,
                    arc_id=card.arc_id,
                    pov_character_id=None,
                )
            )
            card = card.model_copy(update={"episode_id": episode.id, "arc_id": card.arc_id})
            plan = self.repository.create_episode_plan(
                EpisodePlanCreate(
                    novel_id=payload.novel_id,
                    episode_id=episode.id,
                    arc_id=card.arc_id,
                    arc_number=card.arc_number,
                    plan_json=card.model_dump(),
                    objective=card.objective,
                    theme=card.theme,
                    hook_opening=card.hook_opening,
                    ending_hook=card.cliffhanger,
                    continuity_notes={"arc_title": card.arc_title, "episode_number": card.episode_number},
                    assumptions=["episode_cycle_uses_approved_arcs"],
                )
            )
            episode_cards.append(card)
            episode_ids.append(episode.id)
            plan_ids.append(plan["id"])

        score = 0.92 if len(episode_cards) >= 20 else 0.87
        similarity = cosine_similarity(arc_embedding, self.embedder.embed_text(payload.novel_id))
        score = min(0.98, score + similarity * 0.01)

        return EpisodeCycleOutput(
            episode_cards=episode_cards,
            assumptions=["episode_plans_store_episode_card_json", "episodes_created_before_detail_stage"],
            retrieved_memory_document_ids=[getattr(document, "id", "") for document in memory_documents],
            approval_score=score,
            critical_issues=[],
        )

    def _build_episode_card(self, novel_id: str, episode_number: int, arc: object) -> EpisodeCard:
        theme = f"{arc.title}의 {episode_number}화 전개"
        return EpisodeCard(
            episode_number=episode_number,
            arc_number=arc.arc_number,
            arc_title=arc.title,
            arc_id=getattr(arc, "arc_id", None),
            episode_id=f"{novel_id}-ep-{episode_number:03d}",
            title_working=f"{arc.title} {episode_number}화",
            objective=f"{arc.objective}를 한 단계 진전시킨다.",
            theme=theme,
            hook_opening=f"{arc.title}의 새로운 갈등이 열린다.",
            conflict=arc.conflict,
            outcome=f"{arc.payoff}로 이어지는 발판을 만든다.",
            cliffhanger=f"{arc.title}의 다음 전개를 당기기 위한 마지막 변수로 마무리한다.",
            target_length=5000 if episode_number % 2 else 5200,
            scene_count=4 if episode_number % 5 else 5,
            pov_hint="주인공",
        )
