from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, join_fields
from packages.embeddings import EmbedderFactory
from packages.schemas.agent_schemas import (
    CharacterStateSpec,
    ContinuityJudgeInput,
    TimelineEventSpec,
    ValidationResult,
    ValidationSeverity,
)


@dataclass(slots=True)
class ContinuityJudgeAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    embedder: Any = field(init=False, repr=False, default=None)
    last_validation_record: dict[str, object] | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()

    def run(self, payload: ContinuityJudgeInput) -> ValidationResult:
        issues: list[str] = []

        issues.extend(self._detect_character_conflicts(payload.character_states))
        issues.extend(self._detect_timeline_conflicts(payload.timeline_events))
        issues.extend(self._detect_scene_alignment_conflicts(payload.draft_text, payload.scene_beats))

        severity = self._severity_from_issues(issues)
        blocking_decision = severity == ValidationSeverity.CRITICAL
        suggested_fix = self._suggest_fix(issues)
        score = self._score_validation(payload.draft_text, payload.scene_beats, payload.character_states, payload.timeline_events, issues)

        record = self.repository.create_validation(
            novel_id=payload.novel_id,
            target_entity_type="draft",
            target_entity_id=payload.draft_id,
            validation_type="continuity",
            issues=issues,
            severity=severity.value,
            blocking_decision=blocking_decision,
            score=score,
            suggested_fix=suggested_fix,
        )
        self.last_validation_record = record

        return ValidationResult(
            issues=issues,
            severity=severity,
            blocking_decision=blocking_decision,
            suggested_fix=suggested_fix,
        )

    def _detect_character_conflicts(self, character_states: list[CharacterStateSpec]) -> list[str]:
        conflicts: list[str] = []
        seen_states: dict[str, tuple[str, str]] = {}
        for character_state in character_states:
            normalized_state = join_fields(character_state.current_state, character_state.location, character_state.emotion)
            previous = seen_states.get(character_state.character_id)
            if previous is None:
                seen_states[character_state.character_id] = (character_state.character_name, normalized_state)
                continue
            previous_name, previous_state = previous
            if previous_state != normalized_state:
                conflicts.append(f"character_state_conflict:{character_state.character_id}")
            if previous_name and character_state.character_name and previous_name != character_state.character_name:
                conflicts.append(f"character_name_conflict:{character_state.character_id}")
        return conflicts

    def _detect_timeline_conflicts(self, timeline_events: list[TimelineEventSpec]) -> list[str]:
        issues: list[str] = []
        absolute_orders = [event.absolute_order for event in timeline_events]
        if absolute_orders != sorted(absolute_orders):
            issues.append("timeline_order_inconsistent")
        if len(set(absolute_orders)) != len(absolute_orders):
            issues.append("timeline_duplicate_order")
        return issues

    def _detect_scene_alignment_conflicts(self, draft_text: str, scene_beats: list[object]) -> list[str]:
        if not scene_beats:
            return ["scene_beats_missing"]

        overlap_count = 0
        for beat in scene_beats:
            beat_terms = [
                getattr(beat, "objective", ""),
                getattr(beat, "conflict", ""),
                getattr(beat, "outcome", ""),
                getattr(beat, "emotion_shift", ""),
            ]
            if any(term and term in draft_text for term in beat_terms):
                overlap_count += 1
        if overlap_count == 0:
            return ["scene_alignment_low"]
        return []

    def _severity_from_issues(self, issues: list[str]) -> ValidationSeverity:
        if any(issue.startswith("character_state_conflict") or issue.startswith("timeline_") for issue in issues):
            return ValidationSeverity.CRITICAL
        if any(issue == "scene_alignment_low" for issue in issues):
            return ValidationSeverity.MAJOR
        return ValidationSeverity.MINOR

    def _suggest_fix(self, issues: list[str]) -> str:
        suggestions: list[str] = []
        if any(issue.startswith("character_state_conflict") for issue in issues):
            suggestions.append("캐릭터 상태를 하나의 현재 상태로 정리하세요.")
        if any(issue.startswith("timeline_") for issue in issues):
            suggestions.append("타임라인 사건 순서를 오름차순으로 재정렬하세요.")
        if "scene_alignment_low" in issues:
            suggestions.append("초안이 장면 비트의 목표, 갈등, 결과를 더 직접적으로 반영하도록 보강하세요.")
        if not suggestions:
            suggestions.append("설정 충돌이 없도록 draft_text, scene_beats, character_states, timeline_events를 다시 교차 확인하세요.")
        return " ".join(suggestions)

    def _score_validation(
        self,
        draft_text: str,
        scene_beats: list[object],
        character_states: list[CharacterStateSpec],
        timeline_events: list[TimelineEventSpec],
        issues: list[str],
    ) -> float:
        reference_text = join_fields(
            " ".join(getattr(beat, "objective", "") for beat in scene_beats),
            " ".join(getattr(beat, "conflict", "") for beat in scene_beats),
            " ".join(getattr(beat, "outcome", "") for beat in scene_beats),
            " ".join(state.current_state for state in character_states),
            " ".join(event.event_summary for event in timeline_events),
        )
        draft_embedding = self.embedder.embed_text(draft_text or "draft")
        reference_embedding = self.embedder.embed_text(reference_text or "continuity")
        alignment = cosine_similarity(draft_embedding, reference_embedding)
        issue_penalty = min(0.45, 0.12 * len(issues))
        return max(0.0, min(1.0, 0.95 - issue_penalty + (alignment * 0.05)))