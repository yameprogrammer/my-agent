#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMMAND="${1:-start}"

step() {
    echo ""
    echo "==> $1"
}

venv_python() {
    if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
        echo "Virtual environment not found. Run: ./scripts/run.sh setup" >&2
        exit 1
    fi
    echo "$PROJECT_ROOT/.venv/bin/python"
}

ensure_setup() {
    if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
        return
    fi
    step "Creating virtual environment and installing dependencies..."
    bash "$SCRIPT_DIR/setup.sh"
}

init_db() {
    local python
    python="$(venv_python)"
    step "Initializing database..."
    "$python" main.py --init-db
}

bootstrap_demo() {
    local python
    python="$(venv_python)"
    step "Bootstrapping demo novel..."
    "$python" scripts/bootstrap.py
}

run_tests() {
    local python
    python="$(venv_python)"
    step "Running tests..."
    "$python" -m pytest
}

run_admin() {
    local python streamlit
    python="$(venv_python)"
    streamlit="$PROJECT_ROOT/.venv/bin/streamlit"
    if [[ ! -x "$streamlit" ]]; then
        echo "streamlit not installed. Run: ./scripts/run.sh setup" >&2
        exit 1
    fi
    step "Starting Admin Console (http://localhost:8501)..."
    echo "Press Ctrl+C to stop."
    exec "$streamlit" run apps/admin/main.py
}

show_help() {
    cat <<'EOF'
my-agent run script (Linux / macOS)

Usage:
  ./scripts/run.sh [command]

Commands:
  start      Setup (if needed), init DB, demo novel, launch Admin Console (default)
  setup      Create .venv and install dependencies
  init-db    Initialize SQLite schema
  bootstrap  Create demo novel if the database is empty
  test       Run pytest
  admin      Launch Streamlit Admin Console only
  help       Show this message

Examples:
  ./scripts/run.sh
  ./scripts/run.sh start
  ./scripts/run.sh test
EOF
}

case "$COMMAND" in
    help|-h|--help)
        show_help
        ;;
    setup)
        bash "$SCRIPT_DIR/setup.sh"
        echo "Setup complete."
        ;;
    init-db)
        ensure_setup
        init_db
        ;;
    bootstrap)
        ensure_setup
        bootstrap_demo
        ;;
    test)
        ensure_setup
        run_tests
        ;;
    admin)
        ensure_setup
        run_admin
        ;;
    start)
        ensure_setup
        init_db
        bootstrap_demo
        run_admin
        ;;
    *)
        echo "Unknown command: $COMMAND" >&2
        show_help
        exit 1
        ;;
esac