# Agent instructions (entry point)

**Canonical project rules (security + development):** [`.agents/AGENTS.md`](.agents/AGENTS.md)

This repository is **public on GitHub**. Before any code change, commit, or push:

1. Read `.agents/AGENTS.md` (secrets, production guards, export defaults, checklist).
2. Never commit `.env` or real API keys / tokens.
3. Run: `python scripts/check_no_secrets.py`

Do not duplicate rules here — always update `.agents/AGENTS.md` as the single source of truth.
