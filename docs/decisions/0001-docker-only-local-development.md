# 0001 — Docker-only local development

**Date:** 2026-10-27 · **Status:** Accepted

## Context

Five team members on different machines (macOS on Apple Silicon and Intel, possibly Windows) need
the same PostgreSQL + PostGIS, Python and Node versions. Installing PostGIS locally is the usual
source of "works on my machine" problems.

## Decision

Everything runs in Docker Compose: `db`, `backend`, `frontend`. The only host requirements are
Docker and git. Source folders are bind-mounted for live reload; dependencies live inside the
containers (`/opt/venv`, a `node_modules` volume). The database image is built from the official
multi-arch `postgres:17` image plus the PostGIS package, because the `postgis/postgis` images are
amd64-only and run emulated (slowly) on Apple Silicon.

## Consequences

- One command to start: `docker compose up`.
- Tests, linters and package installs run via `docker compose exec …` (documented in the
  `dev-environment` skill).
- After a dependency change everyone rebuilds: `docker compose up -d --build -V`.
- Images are ~0.6–1 GB each on first build; three containers use well under 1 GB of RAM at idle.
