# my-agent

This repository builds an AI-assisted novel production system. Keep agent work narrow, prefer the existing package boundaries, and link to the source docs instead of duplicating them.

## Working Rules

- Prefer one-touch runners: `.\scripts\run.bat` (Windows) or `./scripts/run.sh` (Unix). They handle venv, DB init, demo bootstrap, and Admin Console.
- Or activate `.venv` manually (`.\.venv\Scripts\Activate.ps1` / `source .venv/bin/activate`) and install deps with `pip install -r requirements-dev.txt`.
- Run the app from the project root. Entry points call `pathsetup.ensure_project_paths()` so both `my_agent` (`src/`) and `packages/` resolve correctly.
- Use `pytest` for validation, and `python main.py --init-db` when checking database initialization behavior.
- Keep changes in the right layer: `src/my_agent/` is the core app and persistence layer, while `packages/` holds agents, orchestration, memory search scope, and shared schemas.
- Treat `packages/orchestrator/workflows.py` as the main integration seam between the core app and the agent layer.

## Ollama Notes

- Ollama is only configured through the embedding layer. See [config/embedding_config.json](config/embedding_config.json) and [packages/embeddings.py](packages/embeddings.py).
- `packages/embeddings.py` already falls back to local/hash embeddings if Ollama or `langchain_community` is unavailable. Preserve that behavior.
- When changing embedding behavior, keep the config keys stable unless there is a coordinated migration.

## Important Behaviors

- SQLite vec0 table creation is optional; schema setup must still work when `sqlite-vec` is missing.
- The memory layer has a Python similarity fallback, so do not assume vector extensions are always installed.
- Validation workflow status values and stored record statuses are intentionally different in some places; check the existing tests before changing status handling.

## Source Docs

- [README.md](README.md) for current run commands and high-level scope.
- [docs/usage_guide.md](docs/usage_guide.md) for setup, workflows, Admin Console, and configuration.
- [docs/handover/03_phase3_complete.md](docs/handover/03_phase3_complete.md) and [docs/handover/04_phase4_complete.md](docs/handover/04_phase4_complete.md) for recent implementation context.
- [novel_blueprint/02_architecture.md](novel_blueprint/02_architecture.md) and [novel_blueprint/05_agents.md](novel_blueprint/05_agents.md) for architecture and agent boundaries.
