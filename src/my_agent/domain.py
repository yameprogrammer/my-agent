from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class RecordStatus(str, Enum):
    CREATED = "CREATED"
    GENERATED = "GENERATED"
    REVIEW_PENDING = "REVIEW_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"


class NovelStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class ArcLevel(str, Enum):
    MAIN = "MAIN"
    SUB = "SUB"
    MINI = "MINI"


class ThreadStatus(str, Enum):
    PLANTED = "PLANTED"
    REINFORCED = "REINFORCED"
    RESOLVED = "RESOLVED"
    ABANDONED = "ABANDONED"


class DraftKind(str, Enum):
    CONCEPT = "CONCEPT"
    MASTER_PLAN = "MASTER_PLAN"
    ARC_PLAN = "ARC_PLAN"
    EPISODE_CYCLE = "EPISODE_CYCLE"
    EPISODE_DETAIL = "EPISODE_DETAIL"
    EPISODE_DRAFT = "EPISODE_DRAFT"
    REVISION_NOTE = "REVISION_NOTE"


@dataclass(slots=True)
class BaseEntity:
    novel_id: str
    id: str = field(default_factory=lambda: str(uuid4()), init=False)


@dataclass(slots=True)
class Novel(BaseEntity):
    title: str = ""
    genre: str = "fantasy"
    target_format: str = "webnovel"
    status: NovelStatus = NovelStatus.DRAFT
    current_revision_id: str | None = None


@dataclass(slots=True)
class Character(BaseEntity):
    name: str = ""
    role: str = ""
    revision_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Arc(BaseEntity):
    title: str = ""
    arc_level: ArcLevel = ArcLevel.MAIN
    order_index: int = 0
    status: RecordStatus = RecordStatus.CREATED
    revision_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class Episode(BaseEntity):
    episode_number: int = 0
    title_working: str = ""
    arc_id: str | None = None
    pov_character_id: str | None = None
    status: RecordStatus = RecordStatus.CREATED
    approved_revision_id: str | None = None


@dataclass(slots=True)
class Scene(BaseEntity):
    episode_id: str
    scene_order: int = 0
    objective: str = ""
    conflict: str = ""
    outcome: str = ""


@dataclass(slots=True)
class Thread(BaseEntity):
    thread_type: str = ""
    planted_episode_id: str | None = None
    latest_episode_id: str | None = None
    planned_payoff_episode_id: str | None = None
    status: ThreadStatus = ThreadStatus.PLANTED
    importance: int = 1
    revision_id: str = field(default_factory=lambda: str(uuid4()))
