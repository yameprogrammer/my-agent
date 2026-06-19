from __future__ import annotations

from pathlib import Path

from apps.admin.workflow_helpers import (
    build_draft_validation_state,
    build_episode_to_draft_state,
    build_theme_to_arcs_state,
)
from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate
from packages.orchestrator.workflows import (
    build_draft_validation_workflow,
    build_episode_to_draft_workflow,
    build_theme_to_arcs_workflow,
)


def _create_resources(tmp_path: Path) -> tuple[NovelRepository, MemoryStore]:
    db_path = tmp_path / "admin.db"
    repo = NovelRepository(db_path)
    memory = MemoryStore(db_path)
    repo.create_novel(NovelCreate(novel_id="novel-admin", title="Admin Test Novel"))
    return repo, memory


def test_admin_theme_to_arcs_workflow(tmp_path: Path) -> None:
    repo, memory = _create_resources(tmp_path)
    workflow = build_theme_to_arcs_workflow(repo, memory)
    result = workflow.invoke(build_theme_to_arcs_state("novel-admin", user_preferences="회귀 판타지"))

    assert result["theme_decision"]["approved"] is True
    assert result["arc_decision"]["approved"] is True
    assert repo.list_arcs("novel-admin")


def test_admin_episode_to_draft_after_theme(tmp_path: Path) -> None:
    repo, memory = _create_resources(tmp_path)
    theme_workflow = build_theme_to_arcs_workflow(repo, memory)
    theme_workflow.invoke(build_theme_to_arcs_state("novel-admin"))

    episode_workflow = build_episode_to_draft_workflow(repo, memory)
    result = episode_workflow.invoke(build_episode_to_draft_state(repo, "novel-admin"))

    assert result["cycle_decision"]["approved"] is True
    assert result["draft_decision"]["approved"] is True
    assert result["draft_output"]["draft_text"]


def test_admin_draft_validation_workflow(tmp_path: Path) -> None:
    repo, memory = _create_resources(tmp_path)
    theme_workflow = build_theme_to_arcs_workflow(repo, memory)
    theme_workflow.invoke(build_theme_to_arcs_state("novel-admin"))

    episode_workflow = build_episode_to_draft_workflow(repo, memory)
    episode_workflow.invoke(build_episode_to_draft_state(repo, "novel-admin"))

    validation_workflow = build_draft_validation_workflow(repo, memory)
    result = validation_workflow.invoke(build_draft_validation_state(repo, "novel-admin"))

    assert result["status"] in {"approved", "rejected"}
    assert result["current_stage"] == "Validated"