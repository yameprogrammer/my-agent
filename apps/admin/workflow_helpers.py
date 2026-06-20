from __future__ import annotations

import json
from typing import Any

from my_agent.domain import DraftKind, RecordStatus
from my_agent.repository import NovelRepository
from packages.schemas.agent_schemas import (
    ArcPlanSpec,
    DraftValidationRequest,
    EpisodeToDraftRequest,
    ThemeToArcsRequest,
)

# All workflow state builders in this module are explicitly scoped to a novel_id.
# This supports the project-centric UI layer (current_novel_id from project_context).


def workflow_base_state(novel_id: str) -> dict[str, Any]:
    return {
        "novel_id": novel_id,
        "current_stage": "start",
        "status": "running",
    }


def build_theme_to_arcs_state(
    novel_id: str,
    novel_title: str = "",
    subject: str = "",
    user_preferences: str = "",
    genre_constraints: list[str] | None = None,
    market_positioning: str = "",
) -> dict[str, Any]:
    state = workflow_base_state(novel_id)
    state["request"] = ThemeToArcsRequest(
        novel_id=novel_id,
        novel_title=novel_title or novel_id,
        subject=subject or user_preferences,
        user_preferences=user_preferences,
        genre_constraints=genre_constraints or ["fantasy"],
        market_positioning=market_positioning or "장기 연재용 웹소설",
    )
    return state


def load_approved_arcs(repository: NovelRepository, novel_id: str) -> list[ArcPlanSpec]:
    arc_plan_drafts = repository.list_drafts(novel_id, DraftKind.ARC_PLAN)
    if arc_plan_drafts:
        payload = json.loads(arc_plan_drafts[0].content)
        main_arcs = payload.get("main_arcs", [])
        if main_arcs:
            return [ArcPlanSpec.model_validate(arc) for arc in main_arcs]

    db_arcs = [a for a in repository.list_arcs(novel_id) if a.status != RecordStatus.REJECTED]
    if db_arcs:
        return [
            ArcPlanSpec(
                arc_number=index + 1,
                title=arc.title,
                objective=arc.title,
                conflict="진행 중 갈등",
                payoff="다음 전개",
                episode_range=f"{index * 10 + 1}-{(index + 1) * 10}화",
            )
            for index, arc in enumerate(db_arcs)
        ]

    return [
        ArcPlanSpec(
            arc_number=1,
            title="각성",
            objective="주인공 각성",
            conflict="첫 충돌",
            payoff="첫 보상",
            episode_range="1-10화",
        ),
    ]


def build_episode_to_draft_state(
    repository: NovelRepository,
    novel_id: str,
    selected_episode_number: int = 1,
    target_episode_count: int = 20,
) -> dict[str, Any]:
    state = workflow_base_state(novel_id)
    state["request"] = EpisodeToDraftRequest(
        novel_id=novel_id,
        approved_arcs=load_approved_arcs(repository, novel_id),
        target_episode_count=target_episode_count,
        selected_episode_number=selected_episode_number,
    )
    return state


def build_draft_validation_state(
    repository: NovelRepository,
    novel_id: str,
    draft_id: str | None = None,
    draft_text: str | None = None,
) -> dict[str, Any]:
    """Build state for draft validation.

    If draft_id or draft_text is provided, use it (for episode-specific validation).
    Otherwise fall back to the latest EPISODE_DRAFT for the novel.
    """
    target_draft = None
    if draft_id:
        drafts = repository.list_drafts(novel_id, DraftKind.EPISODE_DRAFT)
        target_draft = next((d for d in drafts if d.id == draft_id), None)

    if not target_draft:
        episode_drafts = repository.list_drafts(novel_id, DraftKind.EPISODE_DRAFT)
        if episode_drafts:
            target_draft = episode_drafts[0]

    if target_draft:
        text = draft_text or target_draft.content
        used_draft_id = target_draft.id
    else:
        used_draft_id = draft_id or "draft-pending"
        text = draft_text or "주인공은 첫 충돌을 지나 결과를 확인한다."

    state = workflow_base_state(novel_id)
    state["current_stage"] = "DraftWritten"
    state["request"] = DraftValidationRequest(
        novel_id=novel_id,
        draft_id=used_draft_id,
        draft_text=text,
    )
    return state