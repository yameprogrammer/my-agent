from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate, MemoryDocumentCreate
from packages.agents.master_planner_agent import MasterPlannerAgent
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import get_agent_search_scope
from packages.schemas.agent_schemas import ConceptCandidate, MasterPlannerInput


def test_master_planner_agent_output_and_scope(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    repo.create_concept("novel-1", "회귀한 검사의 제국 재건", "회귀와 성장", 0.9, True)
    repo.create_theme("novel-1", "성장", "성장과 복권")
    repo.create_world_rule("novel-1", "power_growth", "성장은 누적 선택의 결과다.")

    memory_store = MemoryStore(tmp_path / "memory.db")
    memory_store.upsert_memory_document(
        MemoryDocumentCreate(
            novel_id="novel-1",
            doc_type="theme",
            source_entity_type="theme",
            source_entity_id="t1",
            summary_text="성장형 회귀 판타지",
            metadata_json={},
        )
    )

    agent = MasterPlannerAgent(repo, memory_store, EmbedderFactory(mode="local"), get_agent_search_scope("master_planner"))
    output = agent.run(
        MasterPlannerInput(
            novel_id="novel-1",
            recommended_concept=ConceptCandidate(
                title="회귀한 검사의 제국 재건",
                core_theme="회귀와 성장",
                hook="두 번째 삶에서 제국을 되찾는 성장 서사",
                commercial_score=0.95,
                rationale=["scope=theme_scout"],
            ),
            genre_rules=["fantasy", "growth"],
            thematic_context=["회귀", "성장"],
        )
    )

    assert output.logline
    assert len(output.world_rules) >= 3
    assert output.approval_score >= 0.85
    assert output.retrieved_memory_document_ids
