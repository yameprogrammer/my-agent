from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def ensure_project_paths() -> Path:
    """Put src/ (my_agent) and project root (packages) on sys.path."""
    for entry in (SRC, ROOT):
        text = str(entry)
        if text not in sys.path:
            sys.path.insert(0, text)
    return ROOT