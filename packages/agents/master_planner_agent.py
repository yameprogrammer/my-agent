from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, join_fields
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import SearchScope, get_agent_search_scope, load_repository_context, load_scoped_documents
from packages.schemas.agent_schemas import MasterPlannerInput, MasterPlannerOutput, WorldRuleSpec


@dataclass(slots=True)
class MasterPlannerAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    search_scope: SearchScope | None = None
    embedder: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()
        self.search_scope = self.search_scope or get_agent_search_scope("master_planner")

    def run(self, payload: MasterPlannerInput) -> MasterPlannerOutput:
        repository_context = load_repository_context(self.repository, payload.novel_id, self.search_scope)
        memory_documents = load_scoped_documents(self.memory_store, payload.novel_id, self.search_scope)
        context_text = join_fields(
            payload.recommended_concept.title,
            payload.recommended_concept.core_theme,
            payload.recommended_concept.hook,
            " ".join(payload.genre_rules),
            " ".join(payload.thematic_context),
        )
        query_embedding = self.embedder.embed_text(context_text or payload.novel_id)

        logline = f"{payload.recommended_concept.title}: {payload.recommended_concept.hook}"
        premise = f"판타지 성장형 회귀 서사로, {payload.recommended_concept.core_theme}를 중심으로 장기 연재 구조를 구축한다."
        protagonist_arc = "주인공은 회귀의 기억을 활용해 약함을 강점으로 바꾸며 제국적 규모의 질서를 재편한다."
        ending_direction = "주인공은 개인 생존을 넘어 세계 구조를 재설계하는 결말로 향한다."

        world_rules = self._build_world_rules(payload, repository_context, query_embedding)
        reversal_points = self._build_reversal_points(payload)
        retrieved_ids = [getattr(document, "id", "") for document in memory_documents]
        score = 0.92 if len(world_rules) >= 3 else 0.86
        critical_issues = [] if payload.genre_rules else ["genre_rule_context_missing"]

        return MasterPlannerOutput(
            logline=logline,
            premise=premise,
            protagonist_core_arc=protagonist_arc,
            ending_direction=ending_direction,
            world_rules=world_rules,
            major_reversal_points=reversal_points,
            assumptions=self._build_assumptions(payload, repository_context),
            retrieved_memory_document_ids=retrieved_ids,
            approval_score=score,
            critical_issues=critical_issues,
        )

    def _build_world_rules(
        self,
        payload: MasterPlannerInput,
        repository_context: dict[str, list[dict[str, object]]],
        query_embedding: list[float],
    ) -> list[WorldRuleSpec]:
        seed_rules = [
            ("power_growth", "성장은 누적 선택의 결과이며, 회귀는 선택의 기회를 늘리는 장치다."),
            ("faction_pressure", "세력은 성장 속도를 흔들고, 주인공의 선택을 외부에서 압박한다."),
            ("payoff_discipline", "복선은 회수 시점이 오기 전까지 반드시 강화와 변주를 거친다."),
        ]
        existing_theme_text = " ".join(item.get("name", "") for item in repository_context.get("themes", []))
        context_embedding = self.embedder.embed_text(existing_theme_text or payload.novel_id)
        world_rules: list[WorldRuleSpec] = []
        for index, (rule_key, rule_value) in enumerate(seed_rules, start=1):
            rule_embedding = self.embedder.embed_text(join_fields(rule_key, rule_value))
            similarity = cosine_similarity(query_embedding, rule_embedding)
            context_bonus = cosine_similarity(context_embedding, rule_embedding)
            detail = f"{rule_value} (anchor={index}, scope={self.search_scope.name}, score={round(0.7 + similarity * 0.15 + context_bonus * 0.1, 3)})"
            world_rules.append(WorldRuleSpec(rule_key=rule_key, rule_value=detail))
        return world_rules

    def _build_reversal_points(self, payload: MasterPlannerInput) -> list[str]:
        return [
            f"{payload.recommended_concept.title}의 전제는 중반부에 반대 세력의 개입으로 뒤집힌다.",
            "주인공의 성장 경로는 한 번의 승리보다 반복되는 손실과 회복으로 단단해진다.",
            "세계관 규칙은 후반부에 더 큰 권력 구조를 드러내며 재해석된다.",
        ]

    def _build_assumptions(self, payload: MasterPlannerInput, repository_context: dict[str, list[dict[str, object]]]) -> list[str]:
        assumptions: list[str] = []
        if repository_context.get("concepts"):
            assumptions.append("selected_concept_has_existing_repository_context")
        if not payload.thematic_context:
            assumptions.append("thematic_context_inferred_from_concept")
        return assumptions
