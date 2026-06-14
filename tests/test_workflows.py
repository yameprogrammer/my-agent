from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate
from packages.orchestrator.workflows import build_theme_to_arcs_workflow
from packages.schemas.agent_schemas import ThemeToArcsRequest


def test_theme_to_arcs_workflow(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    memory_store = MemoryStore(tmp_path / "memory.db")
    workflow = build_theme_to_arcs_workflow(repo, memory_store)

    result = workflow.invoke(
        {
            "request": ThemeToArcsRequest(
                novel_id="novel-1",
                user_preferences="회귀, 성장, 제국",
                genre_constraints=["fantasy", "growth"],
                market_positioning="장기 연재용 판타지",
                target_main_arc_count=3,
                target_sub_arc_count=4,
            ),
            "novel_id": "novel-1",
            "current_stage": "start",
            "status": "running",
        }
    )

    assert result["theme_decision"]["approved"] is True
    assert result["master_decision"]["approved"] is True
    assert result["arc_decision"]["approved"] is True
    assert result["arc_output"]["main_arcs"]
    assert repo.list_concepts("novel-1")
    assert repo.list_themes("novel-1")
    assert repo.list_world_rules("novel-1")
