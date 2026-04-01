#!/usr/bin/env bash
set -euo pipefail

python -m scripts.wait_for_db

exec python -m scripts.run_sync_scheduler
