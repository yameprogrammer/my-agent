from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, join_fields
from packages.embeddings import EmbedderFactory
from packages.schemas.agent_schemas import (
    SceneBeatSpec,
    StyleJudgmentResult,
)

@dataclass(slots=True)
class StyleJudgeAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    embedder: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()

    def judge(self, novel_id: str, draft_id: str | None, draft_text: str, scene_beats: list[SceneBeatSpec], style_rules: list[str]) -> StyleJudgmentResult:
        """
        Evaluates the style, pacing, and readability of the draft based on scene beats and style rules.
        """
        # 1. Analyze Pacing (based on scene beat alignment and text length)
        pacing_score = self._evaluate_pacing(draft_text, scene_beats)
        
        # 2. Analyze Readability (based on sentence structure/length simulation)
        readability_score = self._evaluate_readability(draft_text)
        
        # 3. Analyze Tone Consistency (based on style rules alignment)
        tone_consistency_score, tone_issues = self._evaluate_tone(draft_text, style_rules)
        
        # 4. Analyze Webnovel Fit (based on pacing and readability)
        webnovel_fit_score = (pacing_score + readability_score) // 2
        
        # 5. Generate Rewrite Suggestions
        rewrite_suggestions = self._generate_suggestions(tone_issues, pacing_score, readability_score)
        
        # 6. Calculate Overall Score
        overall_score = (pacing_score + readability_score + tone_consistency_score + webnovel_fit_score) // 4
        
        result = StyleJudgmentResult(
            pacing_score=pacing_score,
            readability_score=readability_score,
            tone_consistency_score=tone_consistency_score,
            webnovel_fit_score=webnovel_fit_score,
            rewrite_suggestions=rewrite_suggestions,
            overall_score=overall_score,
        )
        
        # Save to validations table (merging with continuity as per requirements)
        self.repository.create_validation(
            novel_id=novel_id,
            target_entity_type="draft",
            target_entity_id=draft_id,
            validation_type="style",
            issues=rewrite_suggestions,
            severity="minor" if overall_score >= 70 else "major",
            blocking_decision=False, # Style usually doesn't block unless critical
            score=overall_score / 100.0,
            suggested_fix=f"Overall Style Score: {overall_score}. Suggestions: {' '.join(rewrite_suggestions)}",
        )
        
        return result

    def _evaluate_pacing(self, draft_text: str, scene_beats: list[SceneBeatSpec]) -> int:
        if not scene_beats:
            return 50
        
        # Simple heuristic: check if key beat elements are present in the text
        matches = 0
        for beat in scene_beats:
            beat_content = join_fields(beat.objective, beat.conflict, beat.outcome)
            # Use embedding similarity for a more robust check
            draft_emb = self.embedder.embed_text(draft_text)
            beat_emb = self.embedder.embed_text(beat_content)
            if cosine_similarity(draft_emb, beat_emb) > 0.5:
                matches += 1
        
        ratio = matches / len(scene_beats)
        return int(ratio * 100)

    def _evaluate_readability(self, draft_text: str) -> int:
        # Simulation of readability: check for average sentence length and paragraph breaks
        if not draft_text:
            return 0
        
        paragraphs = [p for p in draft_text.split('\n') if p.strip()]
        if not paragraphs:
            return 0
            
        avg_para_len = len(draft_text) / len(paragraphs)
        # Webnovels prefer shorter paragraphs (e.g., 100-300 chars)
        if 100 <= avg_para_len <= 300:
            return 90
        elif avg_para_len < 100:
            return 80
        else:
            return 60

    def _evaluate_tone(self, draft_text: str, style_rules: list[str]) -> tuple[int, list[str]]:
        if not style_rules:
            return 100, []
            
        issues = []
        total_score = 0
        
        draft_emb = self.embedder.embed_text(draft_text)
        
        for rule in style_rules:
            rule_emb = self.embedder.embed_text(rule)
            sim = cosine_similarity(draft_emb, rule_emb)
            
            if sim < 0.4:
                issues.append(f"Style rule not followed: {rule}")
                total_score += 40
            elif sim < 0.7:
                total_score += 70
            else:
                total_score += 100
                
        avg_score = total_score // len(style_rules)
        return avg_score, issues

    def _generate_suggestions(self, tone_issues: list[str], pacing: int, readability: int) -> list[str]:
        suggestions = list(tone_issues)
        if pacing < 70:
            suggestions.append("장면 비트의 전개가 너무 빠르거나 누락된 부분이 있습니다. 호흡을 조절하세요.")
        if readability < 70:
            suggestions.append("문단 길이가 너무 깁니다. 웹소설 가독성을 위해 문단을 더 자주 나누세요.")
        
        if not suggestions:
            suggestions.append("문체가 전반적으로 적절합니다.")
            
        return suggestions
