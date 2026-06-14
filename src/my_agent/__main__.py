from .config import DEFAULT_SQLITE_PATH
from .database import create_engine_and_session, create_schema


def main() -> None:
    engine, _ = create_engine_and_session(DEFAULT_SQLITE_PATH)
    create_schema(engine)
    print(f"SQLite ready: {DEFAULT_SQLITE_PATH}")


if __name__ == "__main__":
    main()
