from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, extract_keywords, join_fields
from packages.embeddings import EmbedderFactory
from packages.llm.base import LLMClient
from packages.memory.search_scope import SearchScope, get_agent_search_scope, load_repository_context, load_scoped_documents
from packages.prompts import PromptLoader
from packages.schemas.agent_schemas import ConceptCandidate, ThemeScoutInput, ThemeScoutOutput


@dataclass(slots=True)
class ThemeScoutAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    search_scope: SearchScope | None = None
    embedder: Any = field(init=False, repr=False, default=None)
    llm_client: LLMClient | None = None

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()
        self.search_scope = self.search_scope or get_agent_search_scope("theme_scout")

    def run(self, payload: ThemeScoutInput) -> ThemeScoutOutput:
        repository_context = load_repository_context(self.repository, payload.novel_id, self.search_scope)
        memory_documents = load_scoped_documents(self.memory_store, payload.novel_id, self.search_scope)

        if self.llm_client is not None:
            concept_candidates = self._generate_concepts_with_llm(payload, repository_context, memory_documents)
        else:
            query_text = join_fields(payload.subject or payload.user_preferences, ";".join(payload.genre_constraints), payload.market_positioning)
            query_embedding = self.embedder.embed_text(query_text or payload.novel_id)
            concept_candidates = self._build_candidates(payload, repository_context, memory_documents, query_embedding)

        if not concept_candidates:
            concept_candidates = self._build_candidates(payload, repository_context, memory_documents, self.embedder.embed_text(payload.user_preferences))

        recommended = max(concept_candidates, key=lambda candidate: candidate.commercial_score)
        risk_notes = self._build_risk_analysis(payload, repository_context, memory_documents)

        return ThemeScoutOutput(
            concept_candidates=concept_candidates,
            recommended_concept=recommended,
            core_theme=recommended.core_theme,
            long_run_risk_analysis=risk_notes,
            assumptions=self._build_assumptions(payload, repository_context),
            retrieved_memory_document_ids=[getattr(document, "id", "") for document in memory_documents],
            approval_score=0.91 if len(concept_candidates) >= 3 else 0.86,
            critical_issues=[] if len(risk_notes) <= 2 else ["insufficient_concept_clarity"],
        )

    def _build_candidates(self, payload: ThemeScoutInput, repository_context: dict[str, list[dict[str, object]]], memory_documents: list[object], query_embedding: list[float]) -> list[ConceptCandidate]:
        # Minimal generic fallback only. Prefer LLM or dynamic generation for user title/subject.
        prefs = payload.subject or payload.user_preferences or " ".join(payload.genre_constraints)
        base = prefs.split(',')[0].strip()[:30] or "이세계"
        seed_bank = [
            (f"{base}의 모험", f"{prefs} 기반 성장", f"{base}가 이세계에서 새로운 운명을 맞는다."),
        ]
        existing_context_text = join_fields(
            " ".join(item.get("title", "") for item in repository_context.get("concepts", [])),
            " ".join(item.get("name", "") for item in repository_context.get("themes", [])),
            " ".join(getattr(document, "summary_text", "") for document in memory_documents),
        )
        context_embedding = self.embedder.embed_text(existing_context_text or payload.novel_id)

        candidates: list[ConceptCandidate] = []
        for index, (title, core_theme, hook) in enumerate(seed_bank, start=1):
            candidate_embedding = self.embedder.embed_text(join_fields(title, core_theme, hook))
            similarity = cosine_similarity(query_embedding, candidate_embedding)
            context_bonus = cosine_similarity(context_embedding, candidate_embedding)
            keyword_bonus = 0.02 * len(set(extract_keywords(prefs)) & set(extract_keywords(title)))
            commercial_score = min(0.98, 0.70 + similarity * 0.18 + context_bonus * 0.08 + keyword_bonus)
            candidates.append(
                ConceptCandidate(
                    title=title,
                    core_theme=core_theme,
                    hook=hook,
                    commercial_score=round(commercial_score, 3),
                    long_run_risk=self._candidate_risks(title, payload),
                    rationale=[f"candidate_index={index}", f"scope={self.search_scope.name}"],
                )
            )
        candidates.sort(key=lambda candidate: candidate.commercial_score, reverse=True)
        return candidates

    def _candidate_risks(self, title: str, payload: ThemeScoutInput) -> list[str]:
        risks: list[str] = []
        prefs = (payload.subject or payload.user_preferences or "").lower()
        if "회귀" not in title.lower() and "회귀" not in prefs:
            risks.append("return_mechanic_not_explicit")
        if "성장" not in title.lower() and not any("성장" in item.lower() for item in (payload.genre_constraints or [])):
            risks.append("growth_spine_weak")
        if len(payload.genre_constraints or []) < 2:
            risks.append("genre_constraints_sparse")
        return risks

    def _build_risk_analysis(self, payload: ThemeScoutInput, repository_context: dict[str, list[dict[str, object]]], memory_documents: list[object]) -> list[str]:
        notes: list[str] = []
        if not repository_context.get("themes"):
            notes.append("no_existing_themes_found")
        if not memory_documents:
            notes.append("no_scope_memory_documents_found")
        if not payload.user_preferences:
            notes.append("user_preferences_empty")
        if not payload.market_positioning:
            notes.append("market_positioning_empty")
        return notes

    def _build_assumptions(self, payload: ThemeScoutInput, repository_context: dict[str, list[dict[str, object]]]) -> list[str]:
        assumptions: list[str] = []
        if repository_context.get("concepts"):
            assumptions.append("existing_concepts_can_be_reused_as_reference")
        prefs = (payload.subject or payload.user_preferences or "").lower()
        if "회귀" not in prefs:
            assumptions.append("theme_selected_from_user_subject")
        return assumptions

    def _generate_concepts_with_llm(
        self,
        payload: ThemeScoutInput,
        repository_context: dict[str, list[dict[str, object]]],
        memory_documents: list[object],
    ) -> list[ConceptCandidate]:
        loader = PromptLoader()
        title = payload.novel_title or payload.novel_id
        subject = payload.subject or payload.user_preferences or " ".join(payload.genre_constraints)
        prompt = loader.render(
            "planning/theme_scout_concepts_v1",
            user_preferences=payload.user_preferences,
            genre_constraints=", ".join(payload.genre_constraints),
            market_positioning=payload.market_positioning or "long-running webnovel",
            novel_idea=f"Title: {title}. Core idea: {subject}",
            base_constraints="",
        )
        try:
            text = self.llm_client.generate_text(prompt)
            import json, re
            match = re.search(r'\[[\s\S]*?\]', text)
            if match:
                data = json.loads(match.group(0))
                candidates = []
                for i, d in enumerate(data[:4]):
                    candidates.append(ConceptCandidate(
                        title=d.get("title", f"{title} 컨셉 {i+1}"),
                        core_theme=d.get("core_theme", subject),
                        hook=d.get("hook", f"{title}의 독특한 매력"),
                        commercial_score=0.85 - (i * 0.02),
                        long_run_risk=[],
                        rationale=["llm_research_based", "title_and_subject_aligned"]
                    ))
                if candidates:
                    return candidates
        except Exception:
            pass

        # Smart dynamic fallback based on title and subject, no hard-coded regression empire
        base = (subject or title).split(',')[0].strip()[:40]
        return [
            ConceptCandidate(
                title=f"{base}의 등장",
                core_theme=subject,
                hook=f"{title} - {subject}",
                commercial_score=0.85,
                long_run_risk=["original_concept"],
                rationale=["dynamic_from_title_subject"]
            ),
            ConceptCandidate(
                title=f"{base}의 모순과 성장",
                core_theme=f"{subject}를 통한 캐릭터의 내적 갈등과 발전",
                hook=f"이세계에서 {base}가 보여주는 예상치 못한 면",
                commercial_score=0.82,
                long_run_risk=["character_driven"],
                rationale=["dynamic_from_title_subject"]
            ),
        ]
