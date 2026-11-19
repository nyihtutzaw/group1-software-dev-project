#!/bin/sh
# Cloud Run Jobs for the hosted demo. Same image as the web service; Cloud Run runs one of:
#
#   cloud-run-job.sh migrate   apply migrations, then load demo accounts + sample data
#                              (idempotent; runs before every deploy)
#   cloud-run-job.sh reset     wipe the database first, then do the same
#                              (needs CONFIRM_RESET=wipe-demo-data; "Reset demo data" action)
set -eu

case "${1:-}" in
  migrate) ;;
  reset)
    if [ "${CONFIRM_RESET:-}" != "wipe-demo-data" ]; then
      echo "reset: refusing without CONFIRM_RESET=wipe-demo-data" >&2
      exit 2
    fi
    python -m app.demo_reset
    ;;
  *)
    echo "usage: cloud-run-job.sh migrate|reset" >&2
    exit 2
    ;;
esac

alembic upgrade head

if python -c "from app.core.config import get_settings as s; raise SystemExit(not s().demo_enabled)"; then
  python -m app.seed
  python -m app.features.registry.demo   # labelled synthetic credits for the public registry
else
  echo "seed: demo accounts disabled — skipped"
fi
