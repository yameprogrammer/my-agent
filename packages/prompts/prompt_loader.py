from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any


class PromptLoader:
    """Simple prompt template loader and renderer.

    Supports:
    - File-based templates under a base directory (default: "prompts")
    - Basic variable substitution using string.Template or .format style
    - Pre-defined sections for consistency with novel_blueprint/10_prompts_contracts.md

    Usage:
        loader = PromptLoader()
        prompt = loader.render("episode/scene_writer_v1", episode_number=1, ...)
    """

    def __init__(self, base_path: str | Path = "prompts") -> None:
        self.base_path = Path(base_path)

    def render(self, name: str, **variables: Any) -> str:
        """Render a template by name (without .md extension).

        Supports {var} style via str.format.
        Falls back gracefully if some variables are missing.
        """
        template_path = self._resolve_template_path(name)
        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")

        raw = template_path.read_text(encoding="utf-8")

        # Use .format with safe handling
        try:
            return raw.format(**variables)
        except KeyError:
            # Provide missing keys as empty strings
            from string import Formatter
            formatter = Formatter()
            used_keys = [field_name for _, field_name, _, _ in formatter.parse(raw) if field_name]
            safe_vars = {k: variables.get(k, "") for k in used_keys}
            return raw.format(**safe_vars)

    def render_with_sections(
        self, name: str, **variables: Any
    ) -> dict[str, str]:
        """Render and split into known sections if present.

        Returns dict with keys like 'system', 'task', etc.
        """
        full = self.render(name, **variables)
        sections: dict[str, str] = {}
        current = "full"
        buffer: list[str] = []

        for line in full.splitlines(keepends=True):
            stripped = line.strip()
            if stripped.startswith("# SYSTEM"):
                if buffer:
                    sections[current] = "".join(buffer).strip()
                current = "system"
                buffer = []
            elif stripped.startswith("# TASK"):
                if buffer:
                    sections[current] = "".join(buffer).strip()
                current = "task"
                buffer = []
            elif stripped.startswith("# CONSTRAINTS"):
                if buffer:
                    sections[current] = "".join(buffer).strip()
                current = "constraints"
                buffer = []
            elif stripped.startswith("# MEMORY_CONTEXT"):
                if buffer:
                    sections[current] = "".join(buffer).strip()
                current = "memory_context"
                buffer = []
            elif stripped.startswith("# OUTPUT_SCHEMA"):
                if buffer:
                    sections[current] = "".join(buffer).strip()
                current = "output_schema"
                buffer = []
            else:
                buffer.append(line)

        if buffer:
            sections[current] = "".join(buffer).strip()

        return sections

    def _resolve_template_path(self, name: str) -> Path:
        # Allow both "episode/scene_writer_v1" and "episode/scene_writer_v1.md"
        if name.endswith(".md"):
            return self.base_path / name
        return self.base_path / f"{name}.md"
