from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from my_agent.approval import ApprovalPolicyStore
from my_agent.repository import NovelRepository
from my_agent.schemas import ArcCreate, DraftCreate, MemoryDocumentCreate, NovelCreate
from my_agent.domain import ArcLevel, DraftKind, RecordStatus
from packages.agents.arc_planner_agent import ArcPlannerAgent
from packages.agents.master_planner_agent import MasterPlannerAgent
from packages.agents.theme_scout_agent import ThemeScoutAgent
from packages.embeddings import EmbedderFactory
from packages.schemas.agent_schemas import (
    ArcPlannerInput,
    MasterPlannerInput,
    StageApprovalDecision,
    ThemeScoutInput,
    ThemeToArcsRequest,
    ThemeToArcsWorkflowState,
    WorkflowStage,
)


def _decision_from_score(stage: WorkflowStage, score: float, critical_issues: list[str], policy_store: ApprovalPolicyStore) -> StageApprovalDecision:
    policy = policy_store.load()
    critical = bool(critical_issues) and policy.critical_requires_manual_review
    if critical:
        return StageApprovalDecision(
            stage=stage,
            score=score,
            approved=False,
            requires_manual_review=True,
            reason="critical_issue",
            critical_issues=critical_issues,
        )
    if score >= policy.auto_approve_threshold or score >= policy.auto_approval_ratio:
        return StageApprovalDecision(
            stage=stage,
            score=score,
            approved=True,
            requires_manual_review=False,
            reason="auto_approved",
            critical_issues=critical_issues,
        )
    if score >= policy.manual_review_threshold or score >= policy.manual_review_ratio:
        return StageApprovalDecision(
            stage=stage,
            score=score,
            approved=False,
            requires_manual_review=True,
            reason="manual_review",
            critical_issues=critical_issues,
        )
    return StageApprovalDecision(
        stage=stage,
        score=score,
        approved=False,
        requires_manual_review=True,
        reason="rejected_for_review",
        critical_issues=critical_issues,
    )


def build_theme_to_arcs_workflow(
    repository: NovelRepository,
    memory_store: object,
    approval_policy_path: str | Path = Path("config") / "approval_policy.json",
    embedder_factory: EmbedderFactory | None = None,
) -> Any:
    policy_store = ApprovalPolicyStore(approval_policy_path)
    embedder_factory = embedder_factory or EmbedderFactory(mode="local")

    theme_agent = ThemeScoutAgent(repository=repository, memory_store=memory_store, embedder_factory=embedder_factory)
    master_agent = MasterPlannerAgent(repository=repository, memory_store=memory_store, embedder_factory=embedder_factory)
    arc_agent = ArcPlannerAgent(repository=repository, memory_store=memory_store, embedder_factory=embedder_factory)

    def theme_node(state: ThemeToArcsWorkflowState) -> dict[str, Any]:
        request = state["request"]
        theme_input = ThemeScoutInput(
            novel_id=request.novel_id,
            user_preferences=request.user_preferences,
            genre_constraints=request.genre_constraints,
            market_positioning=request.market_positioning,
        )
        theme_output = theme_agent.run(theme_input)
        theme_decision = _decision_from_score(WorkflowStage.THEME_SCOUTED, theme_output.approval_score, theme_output.critical_issues, policy_store)
        concept_ids = []
        if theme_decision.approved:
            for index, candidate in enumerate(theme_output.concept_candidates):
                created = repository.create_concept(
                    novel_id=request.novel_id,
                    title=candidate.title,
                    summary=f"{candidate.core_theme}: {candidate.hook}",
                    score=candidate.commercial_score,
                    selected=index == 0,
                )
                concept_ids.append(created["id"])
            repository.create_theme(request.novel_id, theme_output.core_theme, theme_output.recommended_concept.hook)
            memory_store.upsert_memory_document(
                MemoryDocumentCreate(
                    novel_id=request.novel_id,
                    doc_type="theme_scout",
                    source_entity_type="concept",
                    source_entity_id=concept_ids[0] if concept_ids else request.novel_id,
                    summary_text=theme_output.core_theme,
                    content_text=theme_output.recommended_concept.hook,
                    metadata_json={"stage": "theme_scout"},
                )
            )
        return {
            "novel_id": request.novel_id,
            "theme_output": theme_output.model_dump(),
            "theme_decision": theme_decision.model_dump(),
            "concept_ids": concept_ids,
            "current_stage": WorkflowStage.THEME_SCOUTED.value,
            "status": "approved" if theme_decision.approved else WorkflowStage.MANUAL_REVIEW.value,
            "halted_reason": None if theme_decision.approved else theme_decision.reason,
        }

    def master_node(state: ThemeToArcsWorkflowState) -> dict[str, Any]:
        request = state["request"]
        theme_output = state["theme_output"]
        master_input = MasterPlannerInput(
            novel_id=request.novel_id,
            recommended_concept=theme_output["recommended_concept"],
            genre_rules=request.genre_constraints,
            thematic_context=[theme_output["core_theme"]],
            memory_summary=theme_output.get("long_run_risk_analysis", []),
        )
        master_output = master_agent.run(master_input)
        master_decision = _decision_from_score(WorkflowStage.MASTER_PLANNED, master_output.approval_score, master_output.critical_issues, policy_store)
        draft = repository.create_draft(
            DraftCreate(
                novel_id=request.novel_id,
                kind=DraftKind.MASTER_PLAN,
                source_entity_type="novel",
                source_entity_id=request.novel_id,
                title="Master Plan",
                content=master_output.model_dump_json(indent=2),
                status=RecordStatus.APPROVED if master_decision.approved else RecordStatus.REVIEW_PENDING,
            )
        )
        for world_rule in master_output.world_rules:
            repository.create_world_rule(request.novel_id, world_rule.rule_key, world_rule.rule_value)
        memory_store.upsert_memory_document(
            MemoryDocumentCreate(
                novel_id=request.novel_id,
                doc_type="master_plan",
                source_entity_type="novel",
                source_entity_id=request.novel_id,
                summary_text=master_output.logline,
                content_text=master_output.premise,
                metadata_json={"stage": "master_plan"},
            )
        )
        return {
            "novel_id": request.novel_id,
            "master_output": master_output.model_dump(),
            "master_decision": master_decision.model_dump(),
            "draft_ids": [draft.id],
            "current_stage": WorkflowStage.MASTER_PLANNED.value,
            "status": "approved" if master_decision.approved else WorkflowStage.MANUAL_REVIEW.value,
            "halted_reason": None if master_decision.approved else master_decision.reason,
        }

    def arc_node(state: ThemeToArcsWorkflowState) -> dict[str, Any]:
        request = state["request"]
        master_output = master_agent.run(
            MasterPlannerInput.model_validate(
                {
                    "novel_id": request.novel_id,
                    "recommended_concept": state["theme_output"]["recommended_concept"],
                    "genre_rules": request.genre_constraints,
                    "thematic_context": [state["theme_output"]["core_theme"]],
                    "memory_summary": state["theme_output"].get("long_run_risk_analysis", []),
                }
            )
        )
        arc_input = ArcPlannerInput(
            novel_id=request.novel_id,
            master_plan=master_output,
            target_main_arc_count=request.target_main_arc_count,
            target_sub_arc_count=request.target_sub_arc_count,
            thematic_context=[state["theme_output"]["core_theme"]],
            memory_summary=master_output.retrieved_memory_document_ids,
        )
        arc_output = arc_agent.run(arc_input)
        arc_decision = _decision_from_score(WorkflowStage.ARCS_PLANNED, arc_output.approval_score, arc_output.critical_issues, policy_store)
        arc_ids: list[str] = []
        if arc_decision.approved:
            for index, arc_plan in enumerate(arc_output.main_arcs):
                arc = repository.create_arc(
                    ArcCreate(
                        novel_id=request.novel_id,
                        title=arc_plan.title,
                        arc_level=ArcLevel.MAIN,
                        order_index=index,
                    )
                )
                arc_ids.append(arc.id)
            for index, sub_arc in enumerate(arc_output.sub_arcs):
                arc = repository.create_arc(
                    ArcCreate(  # type: ignore[name-defined]
                        novel_id=request.novel_id,
                        title=sub_arc.title,
                        arc_level=ArcLevel.SUB,
                        order_index=index,
                    )
                )
                arc_ids.append(arc.id)
            repository.create_draft(
                DraftCreate(
                    novel_id=request.novel_id,
                    kind=DraftKind.ARC_PLAN,
                    source_entity_type="novel",
                    source_entity_id=request.novel_id,
                    title="Arc Plan",
                    content=arc_output.model_dump_json(indent=2),
                    status=RecordStatus.APPROVED,
                )
            )
            memory_store.upsert_memory_document(
                MemoryDocumentCreate(
                    novel_id=request.novel_id,
                    doc_type="arc_plan",
                    source_entity_type="novel",
                    source_entity_id=request.novel_id,
                    summary_text="Arc plan generated",
                    content_text=arc_output.model_dump_json(indent=2),
                    metadata_json={"stage": "arc_plan"},
                )
            )
        return {
            "novel_id": request.novel_id,
            "arc_output": arc_output.model_dump(),
            "arc_decision": arc_decision.model_dump(),
            "arc_ids": arc_ids,
            "current_stage": WorkflowStage.ARCS_PLANNED.value,
            "status": "approved" if arc_decision.approved else WorkflowStage.MANUAL_REVIEW.value,
            "halted_reason": None if arc_decision.approved else arc_decision.reason,
        }

    graph = StateGraph(ThemeToArcsWorkflowState)
    graph.add_node("theme_scout", theme_node)
    graph.add_node("master_plan", master_node)
    graph.add_node("arc_plan", arc_node)

    graph.set_entry_point("theme_scout")

    def route_theme(state: ThemeToArcsWorkflowState) -> str:
        decision = state["theme_decision"]
        return "master_plan" if decision["approved"] else END

    def route_master(state: ThemeToArcsWorkflowState) -> str:
        decision = state["master_decision"]
        return "arc_plan" if decision["approved"] else END

    def route_arc(state: ThemeToArcsWorkflowState) -> str:
        decision = state["arc_decision"]
        return END if decision["approved"] else END

    graph.add_conditional_edges("theme_scout", route_theme, {"master_plan": "master_plan", END: END})
    graph.add_conditional_edges("master_plan", route_master, {"arc_plan": "arc_plan", END: END})
    graph.add_conditional_edges("arc_plan", route_arc, {END: END})
    return graph.compile()
