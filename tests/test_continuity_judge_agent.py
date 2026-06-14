from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.domain import RecordStatus
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate
from packages.agents.continuity_judge_agent import ContinuityJudgeAgent
from packages.embeddings import EmbedderFactory
from packages.schemas.agent_schemas import (
    CharacterStateSpec,
    ContinuityJudgeInput,
    SceneBeatSpec,
    TimelineEventSpec,
    ValidationSeverity,
)


def test_continuity_judge_agent_approves_consistent_draft(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    memory_store = MemoryStore(tmp_path / "memory.db")
    agent = ContinuityJudgeAgent(repo, memory_store, EmbedderFactory(mode="local"))

    result = agent.run(
        ContinuityJudgeInput(
            novel_id="novel-1",
            draft_id="draft-1",
            draft_text="""
            주인공은 첫 충돌을 지나 결과를 확인한다.
            다음 장면에서는 긴장 상승이 이어지고, 이야기의 흐름이 자연스럽게 이어진다.
            """,
            scene_beats=[
                SceneBeatSpec(scene_order=1, objective="첫 충돌을 통과", conflict="첫 충돌", outcome="결과를 확인", emotion_shift="긴장 상승"),
            ],
            character_states=[
                CharacterStateSpec(character_id="c-1", character_name="주인공", current_state="첫 충돌 이후", location="전장", emotion="긴장"),
            ],
            timeline_events=[
                TimelineEventSpec(event_id="e-1", absolute_order=1, event_summary="첫 충돌", relative_time_label="현재"),
            ],
        )
    )

    assert result.blocking_decision is False
    assert result.severity in {ValidationSeverity.MINOR, ValidationSeverity.MAJOR}
    assert result.issues == []
    validations = repo.list_validations("novel-1", "continuity")
    assert len(validations) == 1
    assert validations[0]["status"] == RecordStatus.APPROVED.value


def test_continuity_judge_agent_rejects_conflicting_draft(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    memory_store = MemoryStore(tmp_path / "memory.db")
    agent = ContinuityJudgeAgent(repo, memory_store, EmbedderFactory(mode="local"))

    result = agent.run(
        ContinuityJudgeInput(
            novel_id="novel-1",
            draft_id="draft-2",
            draft_text="주인공은 이미 전장을 떠났지만, 갑자기 같은 장면에서 다시 시작된다.",
            scene_beats=[
                SceneBeatSpec(scene_order=1, objective="첫 충돌을 통과", conflict="첫 충돌", outcome="결과를 확인", emotion_shift="긴장 상승"),
            ],
            character_states=[
                CharacterStateSpec(character_id="c-1", character_name="주인공", current_state="성 안", location="성", emotion="평온"),
                CharacterStateSpec(character_id="c-1", character_name="주인공", current_state="전장", location="전장", emotion="혼란"),
            ],
            timeline_events=[
                TimelineEventSpec(event_id="e-2", absolute_order=2, event_summary="두 번째 사건", relative_time_label="후반"),
                TimelineEventSpec(event_id="e-1", absolute_order=1, event_summary="첫 번째 사건", relative_time_label="초반"),
            ],
        )
    )

    assert result.blocking_decision is True
    assert result.severity is ValidationSeverity.CRITICAL
    assert result.issues
    assert "충돌" in result.suggested_fix or result.suggested_fix
    validations = repo.list_validations("novel-1", "continuity")
    assert len(validations) == 1
    assert validations[0]["status"] == RecordStatus.REJECTED.value
