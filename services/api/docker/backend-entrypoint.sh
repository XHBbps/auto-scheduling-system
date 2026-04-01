#!/usr/bin/env bash
set -euo pipefail

python -m scripts.wait_for_db
alembic upgrade head
python -m scripts.prewarm_snapshots

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
