from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate, MemoryDocumentCreate
from packages.agents.arc_planner_agent import ArcPlannerAgent
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import get_agent_search_scope
from packages.schemas.agent_schemas import ArcPlannerInput, ConceptCandidate, MasterPlannerOutput, WorldRuleSpec


def test_arc_planner_agent_output_and_scope(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    repo.create_theme("novel-1", "성장", "성장과 복권")
    repo.create_world_rule("novel-1", "power_growth", "성장은 누적 선택의 결과다.")

    memory_store = MemoryStore(tmp_path / "memory.db")
    memory_store.upsert_memory_document(
        MemoryDocumentCreate(
            novel_id="novel-1",
            doc_type="master_plan",
            source_entity_type="master_plan",
            source_entity_id="mp-1",
            summary_text="마스터 플랜 요약",
            metadata_json={},
        )
    )

    master_output = MasterPlannerOutput(
        logline="회귀한 검사의 제국 재건",
        premise="판타지 성장형 회귀 서사",
        protagonist_core_arc="주인공의 성장",
        ending_direction="세계 구조를 재설계",
        world_rules=[
            WorldRuleSpec(rule_key="power_growth", rule_value="성장은 누적 선택의 결과다."),
            WorldRuleSpec(rule_key="faction_pressure", rule_value="세력 압박이 서사를 흔든다."),
            WorldRuleSpec(rule_key="payoff_discipline", rule_value="복선은 반드시 회수한다."),
        ],
        major_reversal_points=["중반 전복"],
        retrieved_memory_document_ids=["mp-1"],
        approval_score=0.95,
    )

    agent = ArcPlannerAgent(repo, memory_store, EmbedderFactory(mode="local"), get_agent_search_scope("arc_planner"))
    output = agent.run(
        ArcPlannerInput(
            novel_id="novel-1",
            master_plan=master_output,
            target_main_arc_count=3,
            target_sub_arc_count=4,
            thematic_context=["회귀", "성장"],
        )
    )

    assert len(output.main_arcs) == 3
    assert len(output.sub_arcs) >= 4
    assert output.approval_score >= 0.85
    assert output.retrieved_memory_document_ids
