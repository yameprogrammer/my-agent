from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_EMBEDDING_CONFIG_PATH = Path("config") / "embedding_config.json"
DEFAULT_LOCAL_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMENSION = 384


@dataclass(slots=True)
class LocalEmbedder:
    model_name: str = DEFAULT_LOCAL_MODEL_NAME
    dimension: int = DEFAULT_EMBEDDING_DIMENSION
    _model: Any = field(default=None, init=False, repr=False)

    def embed_text(self, text: str) -> list[float]:
        model = self._load_model()
        if model is not None:
            vector = model.encode([text], normalize_embeddings=True)[0]
            return [float(value) for value in vector]
        return self._hash_embed(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except Exception:
            self._model = None
            return None
        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception:
            self._model = None
        return self._model

    def _hash_embed(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self.dimension
        tokens = text.lower().split()
        vector = [0.0] * self.dimension
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self.dimension):
                byte_value = digest[index % len(digest)]
                sign = 1.0 if byte_value % 2 else -1.0
                vector[index] += sign * ((byte_value / 255.0) - 0.5)
        length = math.sqrt(sum(value * value for value in vector))
        if length == 0.0:
            return vector
        return [value / length for value in vector]


@dataclass(slots=True)
class OllamaEmbedder:
    model_name: str
    base_url: str
    dimension: int = DEFAULT_EMBEDDING_DIMENSION
    _fallback: LocalEmbedder = field(default_factory=LocalEmbedder, init=False, repr=False)

    def embed_text(self, text: str) -> list[float]:
        try:
            from langchain_community.embeddings import OllamaEmbeddings
        except Exception:
            return self._fallback.embed_text(text)
        try:
            embedder = OllamaEmbeddings(model=self.model_name, base_url=self.base_url)
            vector = embedder.embed_query(text)
            return [float(value) for value in vector]
        except Exception:
            return self._fallback.embed_text(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


class EmbedderFactory:
    def __init__(self, mode: str = "local", config_path: str | Path | None = None) -> None:
        self.mode = mode
        self.config_path = Path(config_path) if config_path is not None else DEFAULT_EMBEDDING_CONFIG_PATH
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {
                "mode": "local",
                "local_model_name": DEFAULT_LOCAL_MODEL_NAME,
                "ollama_model_name": "nomic-embed-text",
                "ollama_base_url": "http://localhost:11434",
                "dimension": DEFAULT_EMBEDDING_DIMENSION,
            }
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def create(self) -> LocalEmbedder | OllamaEmbedder:
        if self.mode == "ollama":
            return OllamaEmbedder(
                model_name=self.config.get("ollama_model_name", "nomic-embed-text"),
                base_url=self.config.get("ollama_base_url", "http://localhost:11434"),
                dimension=int(self.config.get("dimension", DEFAULT_EMBEDDING_DIMENSION)),
            )
        return LocalEmbedder(
            model_name=self.config.get("local_model_name", DEFAULT_LOCAL_MODEL_NAME),
            dimension=int(self.config.get("dimension", DEFAULT_EMBEDDING_DIMENSION)),
        )