from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel

from packages.llm.base import LLMClient


class OllamaLLMClient(LLMClient):
    """LLM client backed by Ollama via LangChain.

    Gracefully falls back to StubLLMClient if langchain_ollama or the server is unavailable.
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:7b-instruct",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_name=model_name, **kwargs)
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._stub = None  # lazy fallback

    def _get_llm(self):
        try:
            from langchain_ollama import ChatOllama
        except Exception:
            return None
        try:
            return ChatOllama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=self.temperature,
            )
        except Exception:
            return None

    def _get_fallback(self):
        if self._stub is None:
            from packages.llm.stub_client import StubLLMClient
            self._stub = StubLLMClient(model_name="stub-fallback")
        return self._stub

    def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        llm = self._get_llm()
        if llm is None:
            return self._get_fallback().generate_text(prompt, system_prompt, **kwargs)

        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("user", prompt))

        try:
            response = llm.invoke(messages)
            return str(response.content)
        except Exception:
            return self._get_fallback().generate_text(prompt, system_prompt, **kwargs)

    def generate_structured(
        self,
        prompt: str,
        output_schema: Type[BaseModel],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        llm = self._get_llm()
        if llm is None:
            return self._get_fallback().generate_structured(prompt, output_schema, system_prompt, **kwargs)

        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("user", prompt))

        try:
            structured_llm = llm.with_structured_output(output_schema)
            result = structured_llm.invoke(messages)
            if isinstance(result, output_schema):
                return result
            # Fallback: try to parse if dict-like
            if isinstance(result, dict):
                return output_schema(**result)
            return self._get_fallback().generate_structured(prompt, output_schema, system_prompt, **kwargs)
        except Exception:
            return self._get_fallback().generate_structured(prompt, output_schema, system_prompt, **kwargs)
