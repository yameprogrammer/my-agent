from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .domain import ArcLevel, DraftKind, NovelStatus, RecordStatus, ThreadStatus


class NovelCreate(BaseModel):
    novel_id: str
    title: str = Field(min_length=1)
    genre: str = "fantasy"
    target_format: str = "webnovel"


class NovelRead(BaseModel):
    novel_id: str
    title: str
    genre: str
    target_format: str
    status: NovelStatus
    current_revision_id: str | None = None


class CharacterCreate(BaseModel):
    novel_id: str
    name: str
    role: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CharacterRead(BaseModel):
    id: str
    novel_id: str
    name: str
    role: str
    revision_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArcCreate(BaseModel):
    novel_id: str
    title: str
    arc_level: ArcLevel = ArcLevel.MAIN
    order_index: int = 0


class ArcRead(BaseModel):
    id: str
    novel_id: str
    title: str
    arc_level: ArcLevel
    order_index: int
    status: RecordStatus
    revision_id: str


class EpisodeCreate(BaseModel):
    novel_id: str
    episode_number: int
    title_working: str = ""
    arc_id: str | None = None
    pov_character_id: str | None = None


class EpisodeRead(BaseModel):
    id: str
    novel_id: str
    episode_number: int
    title_working: str
    arc_id: str | None = None
    pov_character_id: str | None = None
    status: RecordStatus
    approved_revision_id: str | None = None


class SceneCreate(BaseModel):
    novel_id: str
    episode_id: str
    scene_order: int
    objective: str = ""
    conflict: str = ""
    outcome: str = ""


class SceneRead(BaseModel):
    id: str
    novel_id: str
    episode_id: str
    scene_order: int
    objective: str
    conflict: str
    outcome: str


class EpisodePlanCreate(BaseModel):
    novel_id: str
    episode_id: str
    arc_id: str | None = None
    arc_number: int
    plan_json: dict[str, Any] = Field(default_factory=dict)
    objective: str = ""
    theme: str = ""
    hook_opening: str = ""
    ending_hook: str = ""
    continuity_notes: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)


class EpisodePlanRead(BaseModel):
    id: str
    novel_id: str
    episode_id: str
    plan_json: dict[str, Any]
    status: RecordStatus


class SceneBeatCreate(BaseModel):
    novel_id: str
    episode_id: str
    scene_order: int
    objective: str = ""
    conflict: str = ""
    outcome: str = ""
    emotion_shift: str = ""
    participants_json: dict[str, Any] = Field(default_factory=dict)
    thread_ops_json: dict[str, Any] = Field(default_factory=dict)


class SceneBeatRead(BaseModel):
    id: str
    novel_id: str
    episode_id: str
    scene_order: int
    objective: str
    conflict: str
    outcome: str
    emotion_shift: str
    participants_json: dict[str, Any]
    thread_ops_json: dict[str, Any]


class ThreadCreate(BaseModel):
    novel_id: str
    thread_type: str
    planted_episode_id: str | None = None
    latest_episode_id: str | None = None
    planned_payoff_episode_id: str | None = None
    status: ThreadStatus = ThreadStatus.PLANTED
    importance: int = 1


class ThreadRead(BaseModel):
    id: str
    novel_id: str
    thread_type: str
    planted_episode_id: str | None = None
    latest_episode_id: str | None = None
    planned_payoff_episode_id: str | None = None
    status: ThreadStatus
    importance: int
    revision_id: str


class DraftCreate(BaseModel):
    novel_id: str
    kind: DraftKind
    source_entity_type: str
    source_entity_id: str | None = None
    title: str
    content: str
    status: RecordStatus = RecordStatus.CREATED


class DraftRead(BaseModel):
    id: str
    novel_id: str
    kind: DraftKind
    source_entity_type: str
    source_entity_id: str | None = None
    title: str
    content: str
    status: RecordStatus
    created_at: datetime
    updated_at: datetime


class MemoryDocumentCreate(BaseModel):
    novel_id: str
    doc_type: str
    source_entity_type: str
    source_entity_id: str | None = None
    summary_text: str
    content_text: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None


class MemoryDocumentRead(BaseModel):
    id: str
    novel_id: str
    doc_type: str
    source_entity_type: str
    source_entity_id: str | None = None
    summary_text: str
    metadata_json: dict[str, Any]
    embedding: list[float] | None = None


class ApprovalPolicy(BaseModel):
    auto_approve_threshold: float = 0.85
    manual_review_threshold: float = 0.6
    auto_approval_ratio: float = 0.85
    manual_review_ratio: float = 0.15
    critical_requires_manual_review: bool = True
    critical_issue_codes: list[str] = Field(
        default_factory=lambda: ["continuity_blocker", "timeline_error", "pov_break"]
    )
    stage_overrides: dict[str, float] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    is_critical: bool = False
    issues: list[str] = Field(default_factory=list)
    score: float | None = None
