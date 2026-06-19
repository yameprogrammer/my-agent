from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathsetup import ensure_project_paths

ensure_project_paths()

from my_agent.config import DEFAULT_SQLITE_PATH
from my_agent.repository import NovelRepository
from my_agent.schemas import NovelCreate

DEMO_NOVEL_ID = "demo-novel-001"
DEMO_TITLE = "회귀 용사의 밤 (Demo)"


def main() -> int:
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    repo = NovelRepository(DEFAULT_SQLITE_PATH)
    if repo.list_novels():
        print("Demo bootstrap skipped: novels already exist.")
        return 0

    novel = repo.create_novel(
        NovelCreate(
            novel_id=DEMO_NOVEL_ID,
            title=DEMO_TITLE,
            genre="fantasy",
            target_format="webnovel",
        )
    )
    print(f"Created demo novel: {novel.novel_id} ({novel.title})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())