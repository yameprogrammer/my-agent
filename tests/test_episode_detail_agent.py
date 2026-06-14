from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import EpisodeCreate, NovelCreate
from packages.agents.episode_detail_agent import EpisodeDetailAgent
from packages.embeddings import EmbedderFactory
from packages.schemas.agent_schemas import EpisodeCard, EpisodeDetailInput


def test_episode_detail_agent_creates_scene_beats_and_persists(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    episode = repo.create_episode(
        EpisodeCreate(
            novel_id="novel-1",
            episode_number=1,
            title_working="각성 1화",
            arc_id=None,
            pov_character_id=None,
        )
    )
    memory_store = MemoryStore(tmp_path / "memory.db")
    agent = EpisodeDetailAgent(repo, memory_store, EmbedderFactory(mode="local"))

    output = agent.run(
        EpisodeDetailInput(
            novel_id="novel-1",
            episode_card=EpisodeCard(
                episode_number=1,
                arc_number=1,
                arc_title="각성",
                episode_id=episode.id,
                title_working="각성 1화",
                objective="주인공 각성",
                theme="각성",
                hook_opening="첫 갈등",
                conflict="첫 충돌",
                outcome="첫 결과",
                cliffhanger="다음 화 유도",
            ),
            open_threads=["떡밥1"],
            style_rules=["짧은 문장"],
        )
    )

    assert 3 <= len(output.scene_beats) <= 6
    assert repo.list_scene_beats("novel-1")
    assert output.approval_score >= 0.85
