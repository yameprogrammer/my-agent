from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel


class LLMClient(ABC):
    """Abstract base for LLM clients used by agents.

    Supports both plain text generation and structured (Pydantic) output.
    Implementations must be resilient to missing optional dependencies.
    """

    def __init__(self, model_name: str = "stub", **kwargs: Any) -> None:
        self.model_name = model_name
        self.config: dict[str, Any] = kwargs

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate free-form text."""
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        output_schema: Type[BaseModel],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate output that matches the given Pydantic model."""
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}(model={self.model_name})"
