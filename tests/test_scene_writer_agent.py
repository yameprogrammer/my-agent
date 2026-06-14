from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate
from packages.agents.scene_writer_agent import SceneWriterAgent
from packages.embeddings import EmbedderFactory
from packages.schemas.agent_schemas import EpisodeCard, SceneBeatSpec, SceneWriterInput


def test_scene_writer_agent_creates_draft(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    memory_store = MemoryStore(tmp_path / "memory.db")
    agent = SceneWriterAgent(repo, memory_store, EmbedderFactory(mode="local"))

    output = agent.run(
        SceneWriterInput(
            novel_id="novel-1",
            episode_card=EpisodeCard(
                episode_number=1,
                arc_number=1,
                arc_title="각성",
                episode_id="novel-1-ep-001",
                title_working="각성 1화",
                objective="주인공 각성",
                theme="각성",
                hook_opening="첫 갈등",
                conflict="첫 충돌",
                outcome="첫 결과",
                cliffhanger="다음 화 유도",
            ),
            scene_beats=[
                SceneBeatSpec(scene_order=1, objective="목표", conflict="갈등", outcome="결과", emotion_shift="상승"),
                SceneBeatSpec(scene_order=2, objective="목표2", conflict="갈등2", outcome="결과2", emotion_shift="상승2"),
                SceneBeatSpec(scene_order=3, objective="목표3", conflict="갈등3", outcome="결과3", emotion_shift="상승3"),
            ],
            style_rules=["짧은 문장"],
        )
    )

    assert "# 각성 1화" in output.draft_text
    assert repo.list_novels()
    assert output.approval_score >= 0.85
