from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from my_agent.database import create_engine_and_session, create_schema


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 1 bootstrap for the novel system")
    parser.add_argument(
        "--db",
        default=str(Path("data") / "my_agent.db"),
        help="SQLite database path",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Create the SQLite schema",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine, _ = create_engine_and_session(args.db)
    if args.init_db:
        create_schema(engine)
        print(f"Initialized SQLite database at {args.db}")
    else:
        print("Pass --init-db to create the schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())