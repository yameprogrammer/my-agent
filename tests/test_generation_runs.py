from __future__ import annotations

import sqlite3
from pathlib import Path

from my_agent.database import GenerationRunModel, create_engine_and_session, create_schema
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate


def test_generation_runs_schema_has_timestamps(tmp_path: Path) -> None:
    db_path = tmp_path / "novel.db"
    engine, _ = create_engine_and_session(db_path)
    create_schema(engine)

    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(generation_runs)").fetchall()
        }

    assert "created_at" in columns
    assert "updated_at" in columns


def test_generation_runs_migration_adds_timestamps_to_legacy_table(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    engine, _ = create_engine_and_session(db_path)
    GenerationRunModel.__table__.create(engine, checkfirst=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO generation_runs (
                id, novel_id, run_type, input_snapshot_json, retrieved_memory_ids_json,
                prompt_version, model_name, raw_output, parsed_output_json,
                validation_result_json, reviewer_decision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-1",
                "novel-1",
                "theme_to_arcs",
                "{}",
                "[]",
                "v1",
                "local",
                "legacy output",
                "{}",
                "{}",
                "CREATED",
            ),
        )
        connection.commit()

    create_schema(engine)

    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(generation_runs)").fetchall()
        }

    assert "created_at" in columns
    assert "updated_at" in columns


def test_list_generation_runs_returns_recent_first(tmp_path: Path) -> None:
    db_path = tmp_path / "novel.db"
    repo = NovelRepository(db_path)
    repo.create_novel(NovelCreate(novel_id="novel-1", title="Test Novel"))

    with repo.session_factory() as session:
        session.add(
            GenerationRunModel(
                id="run-old",
                novel_id="novel-1",
                run_type="theme_to_arcs",
                raw_output="older",
            )
        )
        session.add(
            GenerationRunModel(
                id="run-new",
                novel_id="novel-1",
                run_type="episode_to_draft",
                raw_output="newer",
            )
        )
        session.commit()

    runs = repo.list_generation_runs("novel-1", limit=10)
    assert len(runs) == 2
    run_types = {run["run_type"] for run in runs}
    assert run_types == {"theme_to_arcs", "episode_to_draft"}
    assert all("created_at" in run for run in runs)