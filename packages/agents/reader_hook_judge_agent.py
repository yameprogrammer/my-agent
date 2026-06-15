from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, join_fields
from packages.embeddings import EmbedderFactory
from packages.schemas.agent_schemas import (
    ReaderHookJudgmentResult,
    EpisodeCard,
)

@dataclass(slots=True)
class ReaderHookJudgeAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    embedder: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()

    def judge(self, novel_id: str, draft_id: str | None, draft_text: str, episode_plan: EpisodeCard, open_threads: list[str]) -> ReaderHookJudgmentResult:
        """
        Evaluates the ending hook of a draft to ensure it pulls the reader into the next episode.
        """
        # 1. Analyze Hook Strength (based on the ending of the draft text)
        hook_strength = self._evaluate_hook_strength(draft_text)
        
        # 2. Analyze Curiosity Gap (based on open threads and the ending)
        curiosity_gap_score = self._evaluate_curiosity_gap(draft_text, open_threads)
        
        # 3. Analyze Emotional Aftertaste (based on the emotional peak at the end)
        emotional_aftertaste_score = self._evaluate_emotional_aftertaste(draft_text)
        
        # 4. Analyze Next Episode Pull (based on the cliffhanger in the episode plan)
        next_episode_pull_score = self._evaluate_pull_strength(draft_text, episode_plan.cliffhanger)
        
        # 5. Generate Hook Suggestions
        hook_suggestions = self._generate_hook_suggestions(
            hook_strength, curiosity_gap_score, emotional_aftertaste_score, next_episode_pull_score
        )
        
        # 6. Calculate Overall Hook Score
        overall_hook_score = (hook_strength + curiosity_gap_score + emotional_aftertaste_score + next_episode_pull_score) // 4
        
        result = ReaderHookJudgmentResult(
            hook_strength=hook_strength,
            curiosity_gap_score=curiosity_gap_score,
            emotional_aftertaste_score=emotional_aftertaste_score,
            next_episode_pull_score=next_episode_pull_score,
            overall_hook_score=overall_hook_score,
            hook_suggestions=hook_suggestions,
        )
        
        # Save to validations table
        self.repository.create_validation(
            novel_id=novel_id,
            target_entity_type="draft",
            target_entity_id=draft_id,
            validation_type="hook",
            issues=hook_suggestions,
            severity="minor" if overall_hook_score >= 70 else "major",
            blocking_decision=False,
            score=overall_hook_score / 100.0,
            suggested_fix=f"Overall Hook Score: {overall_hook_score}. Suggestions: {' '.join(hook_suggestions)}",
        )
        
        return result

    def _evaluate_hook_strength(self, draft_text: str) -> int:
        if not draft_text:
            return 0
        
        # Analyze the last 20% of the text for "hooky" patterns (questions, sudden reveals, etc.)
        ending_part = draft_text[int(len(draft_text) * 0.8):]
        
        # Heuristic: check for punctuation and sentence structure that suggests a cliffhanger
        score = 50
        if "?" in ending_part: score += 10
        if "!" in ending_part: score += 10
        if "..." in ending_part: score += 10
        if len(ending_part.split('\n')) < 5: score += 10 # Short, punchy ending
        
        return min(score, 100)

    def _evaluate_curiosity_gap(self, draft_text: str, open_threads: list[str]) -> int:
        if not draft_text or not open_threads:
            return 50
        
        # Check if the ending text relates to any of the open threads
        ending_part = draft_text[int(len(draft_text) * 0.8):]
        ending_emb = self.embedder.embed_text(ending_part)
        
        max_sim = 0.0
        for thread in open_threads:
            thread_emb = self.embedder.embed_text(thread)
            sim = cosine_similarity(ending_emb, thread_emb)
            max_sim = max(max_sim, sim)
            
        # High similarity to an open thread at the end creates a strong curiosity gap
        return int(max_sim * 100)

    def _evaluate_emotional_aftertaste(self, draft_text: str) -> int:
        # Simulation: check for emotional keywords in the final paragraphs
        if not draft_text:
            return 0
            
        ending_part = draft_text[int(len(draft_text) * 0.8):].lower()
        emotional_keywords = ["shock", "surprise", "fear", "longing", "despair", "hope", "betrayal", "love"]
        
        matches = sum(1 for word in emotional_keywords if word in ending_part)
        return min(50 + (matches * 10), 100)

    def _evaluate_pull_strength(self, draft_text: str, planned_cliffhanger: str) -> int:
        if not draft_text or not planned_cliffhanger:
            return 50
            
        ending_part = draft_text[int(len(draft_text) * 0.8):]
        ending_emb = self.embedder.embed_text(ending_part)
        cliff_emb = self.embedder.embed_text(planned_cliffhanger)
        
        sim = cosine_similarity(ending_emb, cliff_emb)
        return int(sim * 100)

    def _generate_hook_suggestions(self, strength: int, gap: int, emotion: int, pull: int) -> list[str]:
        suggestions = []
        if strength < 70:
            suggestions.append("The ending is too flat. Try adding a surprising revelation or a provocative question.")
        if gap < 70:
            suggestions.append("The connection to unresolved plot threads is weak. Explicitly tease a mystery.")
        if emotion < 70:
            suggestions.append("The emotional impact is low. Amplify the character's internal reaction to the event.")
        if pull < 70:
            suggestions.append("The transition to the next episode is not compelling. Sharpen the cliffhanger.")
            
        if not suggestions:
            suggestions.append("The hook is strong. Maintain this momentum.")
            
        return suggestions
