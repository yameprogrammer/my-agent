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
    EPISODE_CYCLED = "EpisodeCycled"
    EPISODE_DETAILED = "EpisodeDetailed"
    DRAFT_WRITTEN = "DraftWritten"
    VALIDATING = "Validating"
    VALIDATED = "Validated"
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
    novel_title: str = ""
    subject: str = ""
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
    novel_title: str = ""
    subject: str = ""
    recommended_concept: ConceptCandidate
    genre_rules: list[str] = Field(default_factory=list)
    thematic_context: list[str] = Field(default_factory=list)
    memory_summary: list[str] = Field(default_factory=list)
    user_preferences: str = ""


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


class EpisodeCard(AgentBaseModel):
    episode_number: int
    arc_number: int
    arc_title: str
    arc_id: str | None = None
    episode_id: str
    title_working: str
    objective: str
    theme: str
    hook_opening: str
    conflict: str
    outcome: str
    cliffhanger: str
    target_length: int = 5000
    scene_count: int = 4
    pov_hint: str = ""


class EpisodeCycleInput(AgentBaseModel):
    novel_id: str
    approved_arcs: list[ArcPlanSpec]
    target_episode_count: int = 20
    selected_episode_number: int = 1


class EpisodeCycleOutput(AgentBaseModel):
    episode_cards: list[EpisodeCard] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    retrieved_memory_document_ids: list[str] = Field(default_factory=list)
    approval_score: float = 0.92
    critical_issues: list[str] = Field(default_factory=list)


class SceneBeatSpec(AgentBaseModel):
    scene_order: int
    objective: str
    conflict: str
    outcome: str
    emotion_shift: str
    participants: list[str] = Field(default_factory=list)
    thread_ops: list[str] = Field(default_factory=list)


class EpisodeDetailInput(AgentBaseModel):
    novel_id: str
    episode_card: EpisodeCard
    recent_episode_summaries: list[str] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)
    style_rules: list[str] = Field(default_factory=list)


class EpisodeDetailOutput(AgentBaseModel):
    scene_beats: list[SceneBeatSpec] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    retrieved_memory_document_ids: list[str] = Field(default_factory=list)
    approval_score: float = 0.93
    critical_issues: list[str] = Field(default_factory=list)


class SceneWriterInput(AgentBaseModel):
    novel_id: str
    episode_card: EpisodeCard
    scene_beats: list[SceneBeatSpec]
    style_rules: list[str] = Field(default_factory=list)


class SceneWriterOutput(AgentBaseModel):
    draft_text: str
    draft_title: str
    ending_hook: str
    carryover_notes: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    retrieved_memory_document_ids: list[str] = Field(default_factory=list)
    approval_score: float = 0.94
    critical_issues: list[str] = Field(default_factory=list)


class ValidationSeverity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class CharacterStateSpec(AgentBaseModel):
    character_id: str
    character_name: str = ""
    current_state: str = ""
    location: str = ""
    emotion: str = ""


class TimelineEventSpec(AgentBaseModel):
    event_id: str
    absolute_order: int
    event_summary: str
    relative_time_label: str = ""


class ContinuityJudgeInput(AgentBaseModel):
    novel_id: str
    draft_text: str
    scene_beats: list[SceneBeatSpec] = Field(default_factory=list)
    character_states: list[CharacterStateSpec] = Field(default_factory=list)
    timeline_events: list[TimelineEventSpec] = Field(default_factory=list)
    draft_id: str | None = None


class ValidationResult(AgentBaseModel):
    issues: list[str] = Field(default_factory=list)
    severity: ValidationSeverity = ValidationSeverity.MINOR
    blocking_decision: bool = False
    suggested_fix: str = ""


class StyleJudgmentResult(AgentBaseModel):
    pacing_score: int = Field(ge=0, le=100)
    readability_score: int = Field(ge=0, le=100)
    tone_consistency_score: int = Field(ge=0, le=100)
    webnovel_fit_score: int = Field(ge=0, le=100)
    rewrite_suggestions: list[str] = Field(default_factory=list)
    overall_score: int = Field(ge=0, le=100)


class ReaderHookJudgmentResult(AgentBaseModel):
    hook_strength: int = Field(ge=0, le=100)
    curiosity_gap_score: int = Field(ge=0, le=100)
    emotional_aftertaste_score: int = Field(ge=0, le=100)
    next_episode_pull_score: int = Field(ge=0, le=100)
    overall_hook_score: int = Field(ge=0, le=100)
    hook_suggestions: list[str] = Field(default_factory=list)


class EpisodeToDraftRequest(AgentBaseModel):
    novel_id: str
    approved_arcs: list[ArcPlanSpec]
    target_episode_count: int = 20
    selected_episode_number: int = 1


class DraftValidationRequest(AgentBaseModel):
    novel_id: str
    draft_id: str | None = None
    draft_text: str
    scene_beats: list[SceneBeatSpec] = Field(default_factory=list)
    character_states: list[CharacterStateSpec] = Field(default_factory=list)
    timeline_events: list[TimelineEventSpec] = Field(default_factory=list)


class EpisodeToDraftWorkflowState(TypedDict, total=False):
    request: EpisodeToDraftRequest
    cycle_output: EpisodeCycleOutput
    detail_output: EpisodeDetailOutput
    draft_output: SceneWriterOutput
    cycle_decision: StageApprovalDecision
    detail_decision: StageApprovalDecision
    draft_decision: StageApprovalDecision
    current_stage: str
    status: str
    halted_reason: str
    episode_cards: list[EpisodeCard]
    scene_beats: list[SceneBeatSpec]
    episode_ids: list[str]
    episode_plan_ids: list[str]
    scene_beat_ids: list[str]
    draft_ids: list[str]


class DraftValidationWorkflowState(TypedDict, total=False):
    request: DraftValidationRequest
    validation_result: ValidationResult
    validation_record_id: str
    current_stage: str
    status: str
    halted_reason: str


class ThemeToArcsRequest(AgentBaseModel):
    novel_id: str
    novel_title: str = ""
    subject: str = ""
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
