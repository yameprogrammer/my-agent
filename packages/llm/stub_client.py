from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel

from packages.llm.base import LLMClient


class StubLLMClient(LLMClient):
    """Fallback client that returns deterministic stub data.

    Used for tests, development, and when no real LLM is available.
    It tries to return sensible defaults based on the requested schema when possible.
    """

    def __init__(self, model_name: str = "stub", **kwargs: Any) -> None:
        super().__init__(model_name=model_name, **kwargs)

    def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        # Simple deterministic stub text based on prompt keywords
        prompt_lower = prompt.lower()
        if "logline" in prompt_lower or "premise" in prompt_lower or "master" in prompt_lower or "planner" in prompt_lower:
            return (
                "Stub logline: A young hero returns with memories of the future to rebuild an empire. "
                "Premise: Growth through repeated regression and strategic choices in a fantasy world."
            )
        if "화" in prompt or "episode" in prompt_lower or "scene" in prompt_lower or "draft" in prompt_lower or "본문" in prompt:
            return (
                "# 1화 - 각성의 시작\n\n"
                "어둠 속에서 눈을 뜬 주인공은 낯선 천장을 올려다보았다. 기억이 조각조각 떠올랐다. "
                "이곳은 그가 한 번 죽었던 장소였다. 그러나 이번엔 달랐다. 손끝에서 미약한 마나가 느껴졌다.\n\n"
                "그는 천천히 몸을 일으켰다. 주변은 폐허가 된 옛 성이었다. 바람이 스치며 먼지를 일으켰다. "
                "저 멀리 적의 그림자가 보였다. 주인공은 주먹을 쥐었다. 이번 생에서는 절대 지지 않으리라.\n\n"
                "첫 번째 갈등이 시작되었다. 그는 앞으로 나아가야 했다. 적의 그림자가 다가오고 있었다."
            )
        if "arc" in prompt_lower or "아크" in prompt:
            return "Stub arc: Main arc 1 - Awakening and first conflict. Objective: gain power. Payoff: new ally."
        return "Stub generated text. (Prompt length: {})".format(len(prompt))

    def generate_structured(
        self,
        prompt: str,
        output_schema: Type[BaseModel],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        # Try to construct a minimal valid instance of the schema
        try:
            # Many of our schemas have basic fields; provide safe defaults
            field_defaults: dict[str, Any] = {}
            for field_name, field_info in output_schema.model_fields.items():
                if field_info.is_required():
                    annotation = field_info.annotation
                    if annotation is str or (hasattr(annotation, "__origin__") and str in getattr(annotation, "__args__", [])):
                        field_defaults[field_name] = "stub_" + field_name
                    elif annotation is int or annotation is float:
                        field_defaults[field_name] = 0.85
                    elif annotation is list or (hasattr(annotation, "__origin__") and list in getattr(annotation, "__args__", [])):
                        field_defaults[field_name] = []
                    else:
                        field_defaults[field_name] = None
            return output_schema(**field_defaults)  # type: ignore[return-value]
        except Exception:
            # Last resort: try empty construction (will fail for strict schemas)
            return output_schema()  # type: ignore[call-arg]
