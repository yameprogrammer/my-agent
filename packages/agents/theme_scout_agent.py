from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.common import cosine_similarity, extract_keywords, join_fields
from packages.embeddings import EmbedderFactory
from packages.memory.search_scope import SearchScope, get_agent_search_scope, load_repository_context, load_scoped_documents
from packages.schemas.agent_schemas import ConceptCandidate, ThemeScoutInput, ThemeScoutOutput


@dataclass(slots=True)
class ThemeScoutAgent:
    repository: object
    memory_store: object
    embedder_factory: EmbedderFactory | None = None
    search_scope: SearchScope | None = None
    embedder: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self.embedder_factory = self.embedder_factory or EmbedderFactory(mode="local")
        self.embedder = self.embedder_factory.create()
        self.search_scope = self.search_scope or get_agent_search_scope("theme_scout")

    def run(self, payload: ThemeScoutInput) -> ThemeScoutOutput:
        repository_context = load_repository_context(self.repository, payload.novel_id, self.search_scope)
        memory_documents = load_scoped_documents(self.memory_store, payload.novel_id, self.search_scope)
        query_text = join_fields(payload.user_preferences, ";".join(payload.genre_constraints), payload.market_positioning)
        query_embedding = self.embedder.embed_text(query_text or payload.novel_id)

        concept_candidates = self._build_candidates(payload, repository_context, memory_documents, query_embedding)
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
        seed_bank = [
            ("회귀한 검사의 제국 재건", "회귀와 성장", "두 번째 삶에서 제국을 되찾는 성장 서사"),
            ("몰락한 가문의 마도 성장기", "성장과 복권", "무너진 가문을 다시 일으키는 판타지"),
            ("마왕의 시대를 뒤집는 회귀자", "운명 개변", "이미 정해진 멸망을 다시 쓰는 판타지"),
            ("탑과 던전의 질서를 재편하는 영웅", "질서 전복", "세계의 규칙을 바꾸는 대서사"),
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
            keyword_bonus = 0.02 * len(set(extract_keywords(payload.user_preferences)) & set(extract_keywords(title)))
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
        if "회귀" not in title and "회귀" not in payload.user_preferences:
            risks.append("return_mechanic_not_explicit")
        if "성장" not in title and not any("성장" in item for item in payload.genre_constraints):
            risks.append("growth_spine_weak")
        if len(payload.genre_constraints) < 2:
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
        if "회귀" not in payload.user_preferences:
            assumptions.append("theme_selected_from_fantasy_growth_defaults")
        return assumptions
