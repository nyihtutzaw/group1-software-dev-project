#!/bin/sh
# Dev container start-up: bring the schema up to date, load demo users, then serve with reload.
set -e

alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
