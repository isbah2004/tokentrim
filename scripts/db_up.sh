#!/usr/bin/env bash
# Bring up the pgvector-backed Postgres for TokenTrim and verify it end to end.
# Requires Docker with the daemon running. One command:
#
#     ./scripts/db_up.sh
#
# On first boot the schema in db/schema.sql is applied automatically. This
# script then confirms the `vector` extension and `tokentrim_cache` table exist,
# so a green run means the app's DATABASE_URL is ready to use.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> starting pgvector Postgres (docker compose up -d --wait)"
docker compose up -d --wait

echo "==> verifying the vector extension and cache table"
docker compose exec -T db psql -U tokentrim -d tokentrim -v ON_ERROR_STOP=1 \
  -c "\dx vector" \
  -c "\dt tokentrim_cache" \
  -c "SELECT count(*) AS cached_rows FROM tokentrim_cache;"

cat <<'DONE'

DB is ready.
  DATABASE_URL=postgresql://tokentrim:tokentrim@localhost:5432/tokentrim   (already in .env)

Next:
  uvicorn app.main:app --reload     # serve /chat, /stats, dashboard
  docker compose down               # stop the DB (keeps data)
  docker compose down -v            # stop and wipe data
DONE
