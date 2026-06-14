from __future__ import annotations

from pathlib import Path

from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate, MemoryDocumentCreate
from packages.agents.theme_scout_agent import ThemeScoutAgent
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import get_agent_search_scope
from packages.schemas.agent_schemas import ThemeScoutInput
from my_agent.memory import MemoryStore


def test_theme_scout_agent_output_and_scope(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    repo.create_concept("novel-1", "기존 소재", "기존 요약", 0.3)
    repo.create_theme("novel-1", "성장", "성장과 복권")
    repo.create_world_rule("novel-1", "power_growth", "성장은 누적 선택의 결과다.")

    memory_store = MemoryStore(tmp_path / "memory.db")
    memory_store.upsert_memory_document(
        MemoryDocumentCreate(
            novel_id="novel-1",
            doc_type="concept",
            source_entity_type="concept",
            source_entity_id="c1",
            summary_text="회귀와 성장",
            metadata_json={},
        )
    )
    memory_store.upsert_memory_document(
        MemoryDocumentCreate(
            novel_id="novel-1",
            doc_type="episode_summary",
            source_entity_type="episode",
            source_entity_id="e1",
            summary_text="이 문서는 스코프에서 제외되어야 함",
            metadata_json={},
        )
    )

    agent = ThemeScoutAgent(repo, memory_store, EmbedderFactory(mode="local"), get_agent_search_scope("theme_scout"))
    output = agent.run(
        ThemeScoutInput(
            novel_id="novel-1",
            user_preferences="회귀, 성장, 제국",
            genre_constraints=["fantasy", "growth"],
            market_positioning="장기 연재용 판타지",
        )
    )

    assert output.recommended_concept.title
    assert output.approval_score >= 0.85
    assert len(output.retrieved_memory_document_ids) == 1
    assert output.critical_issues == []
