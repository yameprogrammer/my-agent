#!/usr/bin/env bash
# 백업 복원 리허설 — IMP-05
# 사용: ./restore_pg.sh backups/novel_db_YYYYMMDD_HHMMSS.sql.gz
set -euo pipefail

DUMP="${1:-}"
if [[ -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "Usage: $0 path/to/novel_db_*.sql.gz" >&2
  exit 1
fi

echo "WARNING: This overwrites the target database. Ctrl-C within 5s to abort."
sleep 5

if [[ -n "${DATABASE_URL:-}" ]]; then
  URL="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql:\/\/}"
  gunzip -c "$DUMP" | psql "$URL"
elif [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
  export PGPASSWORD="$POSTGRES_PASSWORD"
  gunzip -c "$DUMP" | psql -h "${POSTGRES_HOST:-127.0.0.1}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-novel_db}"
else
  echo "Set DATABASE_URL or POSTGRES_PASSWORD" >&2
  exit 1
fi

echo "Restore finished from $DUMP"
