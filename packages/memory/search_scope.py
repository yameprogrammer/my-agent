from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from my_agent.memory import MemoryStore


@dataclass(frozen=True)
class SearchScope:
    name: str
    allowed_repository_entities: tuple[str, ...]
    allowed_memory_doc_types: tuple[str, ...]
    allowed_source_entity_types: tuple[str, ...]

    def filter_documents(self, documents: Sequence[object]) -> list[object]:
        filtered: list[object] = []
        for document in documents:
            doc_type = getattr(document, "doc_type", None)
            source_entity_type = getattr(document, "source_entity_type", None)
            if self.allowed_memory_doc_types and doc_type not in self.allowed_memory_doc_types:
                continue
            if self.allowed_source_entity_types and source_entity_type not in self.allowed_source_entity_types:
                continue
            filtered.append(document)
        return filtered


AGENT_SEARCH_SCOPES: dict[str, SearchScope] = {
    "theme_scout": SearchScope(
        name="theme_scout",
        allowed_repository_entities=("concepts", "themes"),
        allowed_memory_doc_types=("concept", "theme", "genre_rule"),
        allowed_source_entity_types=("concept", "theme", "world_rule"),
    ),
    "master_planner": SearchScope(
        name="master_planner",
        allowed_repository_entities=("concepts", "themes"),
        allowed_memory_doc_types=("concept", "theme", "genre_rule"),
        allowed_source_entity_types=("concept", "theme", "world_rule"),
    ),
    "arc_planner": SearchScope(
        name="arc_planner",
        allowed_repository_entities=("themes", "world_rules"),
        allowed_memory_doc_types=("master_plan", "theme", "world_rule"),
        allowed_source_entity_types=("theme", "world_rule", "master_plan"),
    ),
    "episode_cycle": SearchScope(
        name="episode_cycle",
        allowed_repository_entities=("arcs", "episodes", "episode_plans"),
        allowed_memory_doc_types=("arc_plan", "master_plan", "theme_scout"),
        allowed_source_entity_types=("novel", "arc", "master_plan", "concept"),
    ),
    "episode_detail": SearchScope(
        name="episode_detail",
        allowed_repository_entities=("episodes", "episode_plans", "scene_beats"),
        allowed_memory_doc_types=("episode_cycle", "episode_plan", "scene_beat"),
        allowed_source_entity_types=("episode", "novel", "scene_beat"),
    ),
    "scene_writer": SearchScope(
        name="scene_writer",
        allowed_repository_entities=("episodes", "episode_plans", "scene_beats"),
        allowed_memory_doc_types=("episode_cycle", "episode_plan", "scene_beat", "draft"),
        allowed_source_entity_types=("episode", "scene_beat", "draft"),
    ),
}


def get_agent_search_scope(agent_name: str) -> SearchScope:
    return AGENT_SEARCH_SCOPES[agent_name]


def load_repository_context(repository: object, novel_id: str, scope: SearchScope) -> dict[str, list[dict[str, object]]]:
    context: dict[str, list[dict[str, object]]] = {}
    if "concepts" in scope.allowed_repository_entities and hasattr(repository, "list_concepts"):
        context["concepts"] = repository.list_concepts(novel_id)
    if "themes" in scope.allowed_repository_entities and hasattr(repository, "list_themes"):
        context["themes"] = repository.list_themes(novel_id)
    if "world_rules" in scope.allowed_repository_entities and hasattr(repository, "list_world_rules"):
        context["world_rules"] = repository.list_world_rules(novel_id)
    if "episodes" in scope.allowed_repository_entities and hasattr(repository, "list_episodes"):
        context["episodes"] = repository.list_episodes(novel_id)
    if "episode_plans" in scope.allowed_repository_entities and hasattr(repository, "list_episode_plans"):
        context["episode_plans"] = repository.list_episode_plans(novel_id)
    if "scene_beats" in scope.allowed_repository_entities and hasattr(repository, "list_scene_beats"):
        context["scene_beats"] = repository.list_scene_beats(novel_id)
    return context


def load_scoped_documents(memory_store: MemoryStore, novel_id: str, scope: SearchScope) -> list[object]:
    return memory_store.list_documents(
        novel_id,
        doc_types=list(scope.allowed_memory_doc_types) if scope.allowed_memory_doc_types else None,
        source_entity_types=list(scope.allowed_source_entity_types) if scope.allowed_source_entity_types else None,
    )
