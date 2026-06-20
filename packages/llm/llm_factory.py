from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.llm.base import LLMClient
from packages.llm.stub_client import StubLLMClient

DEFAULT_LLM_CONFIG_PATH = Path("config") / "llm_config.json"


class LLMFactory:
    """Factory for creating LLMClient instances.

    Mirrors the design of EmbedderFactory for consistency.
    """

    def __init__(
        self,
        mode: str | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path is not None else DEFAULT_LLM_CONFIG_PATH
        self.config = self._load_config()
        self.mode = mode or self.config.get("mode", "stub")

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {
                "mode": "stub",
                "default_model": "qwen2.5:7b-instruct",
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "temperature": 0.65,
                    "max_tokens": 4096,
                },
            }
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return {"mode": "stub"}

    def create(self) -> LLMClient:
        if self.mode == "ollama":
            from packages.llm.ollama_client import OllamaLLMClient

            ollama_cfg = self.config.get("ollama", {})
            return OllamaLLMClient(
                model_name=self.config.get("default_model", "qwen2.5:7b-instruct"),
                base_url=ollama_cfg.get("base_url", "http://localhost:11434"),
                temperature=ollama_cfg.get("temperature", 0.65),
                max_tokens=ollama_cfg.get("max_tokens", 4096),
            )

        # Default to stub (safe, always works)
        return StubLLMClient(
            model_name=self.config.get("default_model", "stub"),
        )
