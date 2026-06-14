from __future__ import annotations

from enum import StrEnum
from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class AgentBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class WorkflowStage(StrEnum):
    THEME_SCOUTED = "ThemeScouted"
    MASTER_PLANNED = "MasterPlanned"
    ARCS_PLANNED = "ArcsPlanned"
    MANUAL_REVIEW = "ManualReview"
    COMPLETED = "Completed"


class StageApprovalDecision(AgentBaseModel):
    stage: WorkflowStage
    score: float = Field(ge=0.0, le=1.0)
    approved: bool
    requires_manual_review: bool
    reason: str
    critical_issues: list[str] = Field(default_factory=list)


class ConceptCandidate(AgentBaseModel):
    title: str
    core_theme: str
    hook: str
    commercial_score: float = Field(ge=0.0, le=1.0)
    long_run_risk: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class ThemeScoutInput(AgentBaseModel):
    novel_id: str
    user_preferences: str = ""
    genre_constraints: list[str] = Field(default_factory=list)
    market_positioning: str = ""


class ThemeScoutOutput(AgentBaseModel):
    concept_candidates: list[ConceptCandidate]
    recommended_concept: ConceptCandidate
    core_theme: str
    long_run_risk_analysis: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    retrieved_memory_document_ids: list[str] = Field(default_factory=list)
    approval_score: float = 0.9
    critical_issues: list[str] = Field(default_factory=list)


class MasterPlannerInput(AgentBaseModel):
    novel_id: str
    recommended_concept: ConceptCandidate
    genre_rules: list[str] = Field(default_factory=list)
    thematic_context: list[str] = Field(default_factory=list)
    memory_summary: list[str] = Field(default_factory=list)


class WorldRuleSpec(AgentBaseModel):
    rule_key: str
    rule_value: str
    category: str = "core"


class MasterPlannerOutput(AgentBaseModel):
    logline: str
    premise: str
    protagonist_core_arc: str
    ending_direction: str
    world_rules: list[WorldRuleSpec] = Field(default_factory=list)
    major_reversal_points: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    retrieved_memory_document_ids: list[str] = Field(default_factory=list)
    approval_score: float = 0.9
    critical_issues: list[str] = Field(default_factory=list)


class ArcPlanSpec(AgentBaseModel):
    arc_number: int
    title: str
    objective: str
    conflict: str
    payoff: str
    episode_range: str


class SubArcPlanSpec(AgentBaseModel):
    arc_number: int
    title: str
    parent_arc_number: int
    objective: str
    payoff: str


class ArcPlannerInput(AgentBaseModel):
    novel_id: str
    master_plan: MasterPlannerOutput
    target_main_arc_count: int = 3
    target_sub_arc_count: int = 6
    thematic_context: list[str] = Field(default_factory=list)
    memory_summary: list[str] = Field(default_factory=list)


class ArcPlannerOutput(AgentBaseModel):
    main_arcs: list[ArcPlanSpec] = Field(default_factory=list)
    sub_arcs: list[SubArcPlanSpec] = Field(default_factory=list)
    arc_dependencies: list[str] = Field(default_factory=list)
    payoff_map: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    retrieved_memory_document_ids: list[str] = Field(default_factory=list)
    approval_score: float = 0.9
    critical_issues: list[str] = Field(default_factory=list)


class ThemeToArcsRequest(AgentBaseModel):
    novel_id: str
    user_preferences: str = ""
    genre_constraints: list[str] = Field(default_factory=list)
    market_positioning: str = ""
    target_main_arc_count: int = 3
    target_sub_arc_count: int = 6


class ThemeToArcsWorkflowState(TypedDict, total=False):
    request: ThemeToArcsRequest
    theme_output: ThemeScoutOutput
    master_output: MasterPlannerOutput
    arc_output: ArcPlannerOutput
    theme_decision: StageApprovalDecision
    master_decision: StageApprovalDecision
    arc_decision: StageApprovalDecision
    current_stage: str
    status: str
    halted_reason: str
    novel_id: str
    concept_ids: list[str]
    theme_ids: list[str]
    arc_ids: list[str]
    draft_ids: list[str]
