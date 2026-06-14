from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate
from packages.agents.episode_cycle_agent import EpisodeCycleAgent
from packages.embeddings import EmbedderFactory
from packages.schemas.agent_schemas import ArcPlanSpec, EpisodeCycleInput


def test_episode_cycle_agent_creates_episode_cards_and_persists(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    memory_store = MemoryStore(tmp_path / "memory.db")
    agent = EpisodeCycleAgent(repo, memory_store, EmbedderFactory(mode="local"))

    output = agent.run(
        EpisodeCycleInput(
            novel_id="novel-1",
            approved_arcs=[
                ArcPlanSpec(arc_number=1, title="각성", objective="주인공 각성", conflict="첫 충돌", payoff="첫 보상", episode_range="1-10화"),
                ArcPlanSpec(arc_number=2, title="확장", objective="세력 확장", conflict="두 번째 충돌", payoff="다음 단계", episode_range="11-20화"),
            ],
            target_episode_count=20,
        )
    )

    assert len(output.episode_cards) == 20
    assert repo.list_episodes("novel-1")
    assert repo.list_episode_plans("novel-1")
    assert output.approval_score >= 0.85
