from __future__ import annotations

import sqlite3
from pathlib import Path

from my_agent.approval import ApprovalPolicyStore
from my_agent.database import create_engine_and_session, create_schema
from my_agent.memory import MemoryStore
from my_agent.repository import NovelRepository
from my_agent.schemas import ArcCreate, CharacterCreate, DraftCreate, EpisodeCreate, MemoryDocumentCreate, NovelCreate, SceneCreate, ThreadCreate


def test_sqlite_connection_and_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "novel.db"
    engine, _ = create_engine_and_session(db_path)
    create_schema(engine)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }

    assert "novels" in tables
    assert "arcs" in tables
    assert "episodes" in tables
    assert "memory_documents" in tables
    assert "drafts" in tables


def test_repository_crud_roundtrip(tmp_path: Path) -> None:
    repo = NovelRepository(tmp_path / "novel.db")
    novel = repo.create_novel(NovelCreate(novel_id="novel-1", title="회귀 용사의 밤", genre="fantasy"))
    character = repo.create_character(CharacterCreate(novel_id="novel-1", name="주인공", role="regressor"))
    arc = repo.create_arc(ArcCreate(novel_id="novel-1", title="각성의 시작"))
    episode = repo.create_episode(EpisodeCreate(novel_id="novel-1", episode_number=1, title_working="첫 화", arc_id=arc.id, pov_character_id=character.id))
    scene = repo.create_scene(SceneCreate(novel_id="novel-1", episode_id=episode.id, scene_order=1, objective="도입", conflict="충돌", outcome="반전"))
    thread = repo.create_thread(ThreadCreate(novel_id="novel-1", thread_type="mystery"))
    draft = repo.create_draft(DraftCreate(novel_id="novel-1", kind="EPISODE_DETAIL", source_entity_type="episode", source_entity_id=episode.id, title="화 설계", content="설계 내용"))

    assert novel.novel_id == "novel-1"
    assert character.novel_id == "novel-1"
    assert arc.novel_id == "novel-1"
    assert episode.arc_id == arc.id
    assert scene.episode_id == episode.id
    assert thread.status.value == "PLANTED"
    assert draft.title == "화 설계"


def test_memory_store_crud(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    created = store.upsert_memory_document(
        MemoryDocumentCreate(
            novel_id="novel-1",
            doc_type="episode_summary",
            source_entity_type="episode",
            source_entity_id="ep-1",
            summary_text="첫 화 요약",
            metadata_json={"arc": "main"},
            embedding=[0.1, 0.2, 0.3],
        )
    )

    fetched = store.get_document(created.id)
    listed = store.list_documents("novel-1")

    assert fetched is not None
    assert fetched.summary_text == "첫 화 요약"
    assert len(listed) == 1
    assert listed[0].metadata_json["arc"] == "main"


def test_approval_policy_roundtrip(tmp_path: Path) -> None:
    policy_path = tmp_path / "approval_policy.json"
    store = ApprovalPolicyStore(policy_path)
    policy = store.load()
    store.save(policy)

    assert policy.auto_approve_threshold == 0.85
    assert policy_path.exists()
    assert store.decide(0.9).approved is True
    assert store.decide(0.5, critical=True).requires_manual_review is True
