from __future__ import annotations

from pathlib import Path

from my_agent.memory import MemoryStore
from my_agent.schemas import MemoryDocumentCreate
from packages.memory.search_scope import get_agent_search_scope, load_scoped_documents


def test_search_scope_filters_memory_documents(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    store.upsert_memory_document(
        MemoryDocumentCreate(
            novel_id="novel-1",
            doc_type="concept",
            source_entity_type="concept",
            source_entity_id="c1",
            summary_text="소재 문서",
            metadata_json={},
        )
    )
    store.upsert_memory_document(
        MemoryDocumentCreate(
            novel_id="novel-1",
            doc_type="episode_summary",
            source_entity_type="episode",
            source_entity_id="e1",
            summary_text="제외 문서",
            metadata_json={},
        )
    )

    scope = get_agent_search_scope("theme_scout")
    documents = load_scoped_documents(store, "novel-1", scope)

    assert [document.doc_type for document in documents] == ["concept"]
