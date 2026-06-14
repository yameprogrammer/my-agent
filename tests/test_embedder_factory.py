from __future__ import annotations

from packages.embeddings import EmbedderFactory


def test_embedder_factory_local_mode() -> None:
    factory = EmbedderFactory(mode="local")
    embedder = factory.create()

    vector = embedder.embed_text("회귀 성장 판타지")

    assert factory.mode == "local"
    assert len(vector) == 384
    assert vector == embedder.embed_text("회귀 성장 판타지")
