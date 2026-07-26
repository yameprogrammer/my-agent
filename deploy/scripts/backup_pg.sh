#!/usr/bin/env bash
# PostgreSQL pg_dump 백업 — IMP-05
# 환경: DATABASE_URL 또는 PG* 변수. 결과는 저장소 backups/ (gitignore).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/novel_db_${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

if [[ -n "${DATABASE_URL:-}" ]]; then
  # postgresql+asyncpg:// → postgresql://
  URL="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql:\/\/}"
  pg_dump "$URL" | gzip -c > "$OUT"
elif [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pg_dump -h "${POSTGRES_HOST:-127.0.0.1}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-novel_db}" \
    | gzip -c > "$OUT"
else
  echo "Set DATABASE_URL or POSTGRES_PASSWORD (+ optional POSTGRES_HOST/USER/DB)" >&2
  exit 1
fi

echo "Wrote $OUT"
# 오래된 백업 정리
find "$BACKUP_DIR" -name 'novel_db_*.sql.gz' -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true
ls -lh "$OUT"
