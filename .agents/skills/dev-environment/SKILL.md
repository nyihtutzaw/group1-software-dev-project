---
name: dev-environment
description: Run the CRVR stack in Docker — start/stop, logs, run backend and frontend tests and linters, add a Python or npm dependency, reset the database, and fix common Docker problems. Use before running any project command; nothing except Docker and git is installed on the host.
---

# Dev environment (Docker only)

Everything runs in containers. Never `pip install`, `uv`, `npm install` or run `pytest` on the host —
run them inside the container with `docker compose exec <service> …` from the repo root.

| Service | URL | Notes |
|---|---|---|
| `frontend` | http://localhost:5173 | Vite dev server, hot reload; proxies `/api` to the backend |
| `backend` | http://localhost:8000/api/docs | FastAPI with `--reload`; runs migrations + seed on start |
| `db` | localhost:5432 | PostgreSQL 17 + PostGIS; user/password/db `crvr`; tests use `crvr_test` |

## Start, stop, look

```bash
docker compose up -d              # start (builds the first time, ~2–3 min)
docker compose ps                 # what is running
docker compose logs -f backend    # follow logs (frontend / db likewise)
docker compose restart backend    # after changing env vars or entrypoint
docker compose down               # stop (data is kept)
```

## Checks — run these before every commit

Run the ones for the side you changed.

```bash
# backend
docker compose exec backend ruff format .
docker compose exec backend ruff check --fix .
docker compose exec backend pytest
docker compose exec backend alembic check          # models and migrations agree

# frontend
docker compose exec frontend npm run format
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test
```

Run one backend test: `docker compose exec backend pytest tests/test_auth.py -k logout`.

## Add a dependency

```bash
# Python (writes pyproject.toml + uv.lock)
docker compose exec backend uv add shapely          # dev-only: uv add --dev <pkg>
docker compose up -d --build backend

# npm (writes package.json + package-lock.json)
docker compose exec frontend npm install leaflet    # dev-only: npm install -D <pkg>
docker compose up -d --build -V frontend            # -V renews the node_modules volume
```

Commit the lock file together with the manifest. Tell the team in the PR — everyone needs to
rebuild after pulling (`docker compose up -d --build -V`).

## Database

```bash
docker compose exec db psql -U crvr crvr                       # SQL shell
docker compose exec backend alembic upgrade head               # apply migrations
docker compose exec backend alembic downgrade -1               # undo the last one
docker compose down -v && docker compose up -d                 # WIPE everything and start fresh
```

Demo accounts (`developer@`, `verifier@`, `staff@`, `buyer@`, `admin@crvr.local`, password
`crvr-demo`) are recreated on every backend start if missing.

## When something is wrong

| Symptom | Fix |
|---|---|
| Port already in use | Another app has 5173/8000/5432. Set `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` in `.env` (copy `.env.example`). |
| `Cannot find module` / import errors after pulling | Dependencies changed: `docker compose up -d --build -V` |
| Code changes not picked up (Windows/WSL) | In `.env`: `WATCHFILES_FORCE_POLLING=true` and `CHOKIDAR_USEPOLLING=true`, then `docker compose up -d` |
| Backend exits on start | `docker compose logs backend` — usually a migration error; fix it or `alembic downgrade -1` |
| Weird DB state | `docker compose down -v && docker compose up -d` (deletes local data) |
| `exec format error` / script errors on Windows | Line endings: `git config core.autocrlf false`, then re-clone (`.gitattributes` keeps LF) |
