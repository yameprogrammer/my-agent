from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, join_fields
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import SearchScope, get_agent_search_scope, load_repository_context, load_scoped_documents
from packages.schemas.agent_schemas import ArcPlanSpec, ArcPlannerInput, ArcPlannerOutput, SubArcPlanSpec


@dataclass(slots=True)
class ArcPlannerAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    search_scope: SearchScope | None = None
    embedder: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()
        self.search_scope = self.search_scope or get_agent_search_scope("arc_planner")

    def run(self, payload: ArcPlannerInput) -> ArcPlannerOutput:
        repository_context = load_repository_context(self.repository, payload.novel_id, self.search_scope)
        memory_documents = load_scoped_documents(self.memory_store, payload.novel_id, self.search_scope)
        master_text = join_fields(
            payload.master_plan.logline,
            payload.master_plan.premise,
            payload.master_plan.protagonist_core_arc,
            payload.master_plan.ending_direction,
            " ".join(rule.rule_value for rule in payload.master_plan.world_rules),
        )
        query_embedding = self.embedder.embed_text(master_text or payload.novel_id)

        main_arcs = self._build_main_arcs(payload, repository_context, query_embedding)
        sub_arcs = self._build_sub_arcs(payload, main_arcs)
        dependencies = [f"main_arc_{index + 1} -> sub_arc_cluster" for index in range(len(main_arcs))]
        payoff_map = {arc.title: arc.payoff for arc in main_arcs}
        retrieved_ids = [getattr(document, "id", "") for document in memory_documents]

        return ArcPlannerOutput(
            main_arcs=main_arcs,
            sub_arcs=sub_arcs,
            arc_dependencies=dependencies,
            payoff_map=payoff_map,
            assumptions=self._build_assumptions(payload, repository_context),
            retrieved_memory_document_ids=retrieved_ids,
            approval_score=0.93 if len(main_arcs) >= 3 else 0.87,
            critical_issues=[] if payload.master_plan.world_rules else ["world_rule_context_missing"],
        )

    def _build_main_arcs(
        self,
        payload: ArcPlannerInput,
        repository_context: dict[str, list[dict[str, object]]],
        query_embedding: list[float],
    ) -> list[ArcPlanSpec]:
        arcs: list[ArcPlanSpec] = []
        theme_count = max(1, len(repository_context.get("themes", [])))
        for index in range(1, payload.target_main_arc_count + 1):
            title = f"{payload.master_plan.logline} {index}막"
            objective = f"{index}번째 주된 목표로 {payload.master_plan.premise}를 강화한다."
            conflict = f"{index}막에서 세력 충돌과 규칙 변화가 확대된다."
            payoff = f"{index}막의 보상은 다음 단계의 성장 재료를 제공한다."
            episode_range = f"{(index - 1) * 30 + 1}-{index * 30}화"
            arc_embedding = self.embedder.embed_text(join_fields(title, objective, conflict, payoff))
            _ = cosine_similarity(query_embedding, arc_embedding) + theme_count * 0.01
            arcs.append(
                ArcPlanSpec(
                    arc_number=index,
                    title=title,
                    objective=objective,
                    conflict=conflict,
                    payoff=payoff,
                    episode_range=episode_range,
                )
            )
        return arcs

    def _build_sub_arcs(self, payload: ArcPlannerInput, main_arcs: list[ArcPlanSpec]) -> list[SubArcPlanSpec]:
        sub_arcs: list[SubArcPlanSpec] = []
        if not main_arcs:
            return sub_arcs
        target = max(payload.target_sub_arc_count, len(main_arcs) * 2)
        for index in range(1, target + 1):
            parent = main_arcs[(index - 1) % len(main_arcs)]
            sub_arcs.append(
                SubArcPlanSpec(
                    arc_number=index,
                    title=f"{parent.title} - 서브 {index}",
                    parent_arc_number=parent.arc_number,
                    objective=f"{parent.title}의 보조 갈등을 가속한다.",
                    payoff=f"{parent.title}의 핵심 보상을 받쳐준다.",
                )
            )
        return sub_arcs

    def _build_assumptions(self, payload: ArcPlannerInput, repository_context: dict[str, list[dict[str, object]]]) -> list[str]:
        assumptions: list[str] = []
        if repository_context.get("world_rules"):
            assumptions.append("existing_world_rules_shape_arc_progression")
        if payload.target_main_arc_count < 3:
            assumptions.append("arc_count_reduced_for_mvp")
        return assumptions
