from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate
from packages.orchestrator.workflows import build_draft_validation_workflow
from packages.schemas.agent_schemas import (
    CharacterStateSpec,
    DraftValidationRequest,
    SceneBeatSpec,
    TimelineEventSpec,
)


def test_validation_workflow_approves_consistent_draft(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    memory_store = MemoryStore(tmp_path / "memory.db")
    workflow = build_draft_validation_workflow(repo, memory_store)

    result = workflow.invoke(
        {
            "request": DraftValidationRequest(
                novel_id="novel-1",
                draft_id="draft-1",
                draft_text="주인공은 첫 충돌을 지나 결과를 확인한다. 다음 장면에서는 긴장 상승이 이어진다.",
                scene_beats=[
                    SceneBeatSpec(scene_order=1, objective="첫 충돌을 통과", conflict="첫 충돌", outcome="결과를 확인", emotion_shift="긴장 상승"),
                ],
                character_states=[
                    CharacterStateSpec(character_id="c-1", character_name="주인공", current_state="첫 충돌 이후", location="전장", emotion="긴장"),
                ],
                timeline_events=[
                    TimelineEventSpec(event_id="e-1", absolute_order=1, event_summary="첫 충돌", relative_time_label="현재"),
                ],
            ),
            "current_stage": "DraftWritten",
            "status": "running",
        }
    )

    assert result["current_stage"] == "Validated"
    assert result["status"] == "approved"
    assert result["validation_result"]["blocking_decision"] is False
    assert repo.list_validations("novel-1", "continuity")


def test_validation_workflow_rejects_conflicting_draft(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤"))
    memory_store = MemoryStore(tmp_path / "memory.db")
    workflow = build_draft_validation_workflow(repo, memory_store)

    result = workflow.invoke(
        {
            "request": DraftValidationRequest(
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
            ),
            "current_stage": "DraftWritten",
            "status": "running",
        }
    )

    assert result["current_stage"] == "Validated"
    assert result["status"] == "rejected"
    assert result["validation_result"]["blocking_decision"] is True
    assert result["validation_result"]["severity"] == "critical"
    assert repo.list_validations("novel-1", "continuity")
