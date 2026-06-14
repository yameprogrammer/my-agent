from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, delete, select, text, update
from sqlalchemy.orm import Session

from .database import MemoryDocumentModel, create_engine_and_session, create_schema, session_scope
from .domain import Novel
from .schemas import MemoryDocumentCreate, MemoryDocumentRead


class MemoryStore:
    def __init__(self, db_path: str | Path):
        self.engine, self.session_factory = create_engine_and_session(db_path)
        self.vector_enabled = False
        create_schema(self.engine)
        self._create_vector_table()

    def _create_vector_table(self) -> None:
        with self.engine.begin() as connection:
            try:
                import sqlite_vec

                raw_connection = connection.connection
                if hasattr(raw_connection, "enable_load_extension"):
                    raw_connection.enable_load_extension(True)
                    sqlite_vec.load(raw_connection)
                    raw_connection.enable_load_extension(False)
                connection.exec_driver_sql(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                        embedding float[384],
                        novel_id TEXT,
                        doc_type TEXT,
                        source_entity_type TEXT,
                        source_entity_id TEXT
                    )
                    """
                )
                self.vector_enabled = True
            except Exception:
                self.vector_enabled = False

    def upsert_memory_document(self, payload: MemoryDocumentCreate) -> MemoryDocumentRead:
        with session_scope(self.session_factory) as session:
            existing = session.execute(
                select(MemoryDocumentModel).where(
                    MemoryDocumentModel.novel_id == payload.novel_id,
                    MemoryDocumentModel.source_entity_type == payload.source_entity_type,
                    MemoryDocumentModel.source_entity_id == payload.source_entity_id,
                    MemoryDocumentModel.doc_type == payload.doc_type,
                )
            ).scalar_one_or_none()
            if existing is None:
                existing = MemoryDocumentModel(
                    id=str(uuid4()),
                    novel_id=payload.novel_id,
                    doc_type=payload.doc_type,
                    source_entity_type=payload.source_entity_type,
                    source_entity_id=payload.source_entity_id,
                    summary_text=payload.summary_text,
                    metadata_json=payload.metadata_json,
                    embedding=json.dumps(payload.embedding) if payload.embedding is not None else None,
                )
                session.add(existing)
            else:
                existing.summary_text = payload.summary_text
                existing.metadata_json = payload.metadata_json
                existing.embedding = json.dumps(payload.embedding) if payload.embedding is not None else None
            session.flush()
            return self._to_read(existing)

    def get_document(self, document_id: str) -> MemoryDocumentRead | None:
        with session_scope(self.session_factory) as session:
            row = session.get(MemoryDocumentModel, document_id)
            return None if row is None else self._to_read(row)

    def list_documents(
        self,
        novel_id: str,
        doc_types: list[str] | None = None,
        source_entity_types: list[str] | None = None,
    ) -> list[MemoryDocumentRead]:
        with session_scope(self.session_factory) as session:
            statement = select(MemoryDocumentModel).where(MemoryDocumentModel.novel_id == novel_id)
            if doc_types:
                statement = statement.where(MemoryDocumentModel.doc_type.in_(doc_types))
            if source_entity_types:
                statement = statement.where(MemoryDocumentModel.source_entity_type.in_(source_entity_types))
            rows = session.execute(statement.order_by(MemoryDocumentModel.doc_type)).scalars().all()
            return [self._to_read(row) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        with session_scope(self.session_factory) as session:
            result = session.execute(delete(MemoryDocumentModel).where(MemoryDocumentModel.id == document_id))
            return result.rowcount > 0

    def search_documents(
        self,
        novel_id: str,
        query_embedding: list[float],
        limit: int = 5,
        doc_types: list[str] | None = None,
        source_entity_types: list[str] | None = None,
    ) -> list[MemoryDocumentRead]:
        with session_scope(self.session_factory) as session:
            statement = select(MemoryDocumentModel).where(MemoryDocumentModel.novel_id == novel_id)
            if doc_types:
                statement = statement.where(MemoryDocumentModel.doc_type.in_(doc_types))
            if source_entity_types:
                statement = statement.where(MemoryDocumentModel.source_entity_type.in_(source_entity_types))
            rows = session.execute(statement).scalars().all()

        scored_rows: list[tuple[float, MemoryDocumentModel]] = []
        for row in rows:
            embedding = self._json_load(row.embedding) or []
            score = self._cosine_similarity(query_embedding, embedding)
            scored_rows.append((score, row))

        scored_rows.sort(key=lambda item: item[0], reverse=True)
        return [self._to_read(row) for _, row in scored_rows[:limit]]

    def _to_read(self, row: MemoryDocumentModel) -> MemoryDocumentRead:
        return MemoryDocumentRead(
            id=row.id,
            novel_id=row.novel_id,
            doc_type=row.doc_type,
            source_entity_type=row.source_entity_type,
            source_entity_id=row.source_entity_id,
            summary_text=row.summary_text,
            metadata_json=row.metadata_json or {},
            embedding=self._json_load(row.embedding),
        )

    @staticmethod
    def _json_load(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        limit = min(len(left), len(right))
        left_slice = left[:limit]
        right_slice = right[:limit]
        dot = sum(l_value * r_value for l_value, r_value in zip(left_slice, right_slice, strict=False))
        left_norm = math.sqrt(sum(value * value for value in left_slice))
        right_norm = math.sqrt(sum(value * value for value in right_slice))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return dot / (left_norm * right_norm)
