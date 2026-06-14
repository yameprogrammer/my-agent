from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate
from packages.orchestrator.workflows import build_episode_to_draft_workflow
from packages.schemas.agent_schemas import ArcPlanSpec, EpisodeToDraftRequest


def test_episode_to_draft_workflow(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    memory_store = MemoryStore(tmp_path / "memory.db")
    workflow = build_episode_to_draft_workflow(repo, memory_store)

    result = workflow.invoke(
        {
            "request": EpisodeToDraftRequest(
                novel_id="novel-1",
                approved_arcs=[
                    ArcPlanSpec(arc_number=1, title="각성", objective="주인공 각성", conflict="첫 충돌", payoff="첫 보상", episode_range="1-10화"),
                    ArcPlanSpec(arc_number=2, title="확장", objective="세력 확장", conflict="두 번째 충돌", payoff="다음 단계", episode_range="11-20화"),
                ],
                target_episode_count=20,
                selected_episode_number=1,
            ),
            "current_stage": "start",
            "status": "running",
        }
    )

    assert result["cycle_decision"]["approved"] is True
    assert result["detail_decision"]["approved"] is True
    assert result["draft_decision"]["approved"] is True
    assert result["draft_output"]["draft_text"]
    assert repo.list_episodes("novel-1")
    assert repo.list_episode_plans("novel-1")
    assert repo.list_scene_beats("novel-1")
    assert repo.list_novels()
