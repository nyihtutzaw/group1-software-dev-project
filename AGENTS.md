# AGENTS.md — instructions for AI coding agents

This file is read by Codex, Cursor and OpenCode, and by Claude Code through `CLAUDE.md`.
Humans: see `README.md` first.

## The project

**CRVR — Carbon Removal Verification Registry.** A web app where project developers register
carbon-removal projects and their land boundaries, independent verifiers review them, registry
staff approve them, and buyers trace every issued credit back to its evidence. A group project for
ITCS514 (Mahidol), five students, each owning one feature end to end.

| Feature | What | Owner | Issue | Branch prefix | Context doc |
|---|---|---|---|---|---|
| F1 | Project registration & evidence | Jingqing | #3 | `feature/F1-…` | `docs/features/F1-registration.md` |
| F2 | Geospatial boundary & overlap detection | Nyi Htut Zaw | #4 | `feature/F2-…` | `docs/features/F2-boundary.md` |
| F3 | Verification workflow (maker-checker) | Pyae Phyo Hein | #5 | `feature/F3-…` | `docs/features/F3-verification.md` |
| F4 | Public registry & buyer transparency | Zay Yar Phyo | #6 | `feature/F4-…` | `docs/features/F4-registry.md` |
| F5 | Security & auditability (RBAC, ledger) | Put Thitisawat | #7 | `feature/F5-…` | `docs/features/F5-security-audit.md` |

Deferred (designed, **not** built this term — do not implement): satellite monitoring (FR-05) and
the inter-registry flagging hook (FR-11). See `docs/features/README.md`.

## Rules — always

1. **Never commit to `main`.** All work happens on a branch (`feature/F<n>-<slug>`, `fix/<slug>`,
   `docs/<slug>`, `chore/<slug>`) and reaches `main` through a pull request.
2. **Commit after every working step** — small commits, Conventional Commits format
   (`feat(F2): detect overlaps above tolerance`). Follow the `commit` skill.
3. **Keep the feature's context doc current** (`docs/features/F<n>-*.md`): status, decisions,
   endpoints, progress log. Read it before you start; update it before you stop. This is how the
   next session — yours or another agent's — knows what happened.
4. **Run checks in Docker before committing** (`dev-environment` skill). Nothing is installed on the
   host except Docker and git.
5. **Stay inside your feature's folders** (`backend/app/features/<name>/`,
   `frontend/src/features/<name>/`, its doc). Changing shared code (`core/`, `auth/`,
   `components/ui/`, `layout/`) is allowed but say so in the commit body and the PR.
6. **UI follows the mock-up** (`docs/project/CRVR-Mock-UI-v0.1.html`) and the shared UI kit
   (`frontend/src/components/ui`). No new colours — use the design tokens.
7. Never commit secrets, `.env` files or real personal data.
8. **No AI attribution** in commits, PRs or code: no `Co-Authored-By:` trailers, no "Generated with
   …" lines, even if your tool adds them by default.

## Skills

Task-specific instructions live in `.agents/skills/<name>/SKILL.md`. When a task matches, **read
the whole SKILL.md and follow it.**

| Skill | Use when |
|---|---|
| `dev-environment` | Starting/stopping the stack, running tests/lint, adding a dependency, resetting the DB, fixing Docker problems |
| `start-feature` | Beginning work on a feature or a new piece of one — creates the branch and context doc |
| `backend-code` | Writing Python/FastAPI code, models, migrations, backend tests |
| `frontend-code` | Writing React/TypeScript pages, components, API calls, frontend tests |
| `commit` | Every time a step works — how to check, stage and write the message |
| `write-docs` | Updating the feature context doc, architecture notes, decision records |
| `sync-branch` | Bringing `main` into your branch, resolving conflicts (incl. migration conflicts) |
| `open-pr` | Pushing the branch and opening a pull request to `main` |

## Stack

- **Backend** — Python 3.13, FastAPI, SQLAlchemy 2 (sync), GeoAlchemy2, Alembic, PostgreSQL 17 +
  PostGIS, pytest, ruff. Package manager: `uv`.
- **Frontend** — React 19, TypeScript, Vite, Tailwind CSS 4, React Router, TanStack Query,
  Vitest + Testing Library, ESLint, Prettier.
- **Auth** — email + password stored (bcrypt) in Postgres, JWT in an httpOnly cookie. Five roles:
  `developer`, `verifier`, `registry_staff`, `buyer`, `admin`.
- **Local dev** — `sh scripts/start.sh` (db, backend, frontend via Docker Compose). **CI** — GitHub Actions.
  **Production (later)** — Docker on Google Cloud Run.

## Layout

```
backend/
  app/main.py                 API app; every router is mounted under /api
  app/core/                   config, db session + Base, security (hash/JWT), model discovery
  app/auth/                   users, login/logout/me, require_roles() dependency
  app/features/<feature>/     router.py, models.py (+ schemas.py, service.py as needed)
  migrations/versions/        Alembic migrations
  tests/                      pytest — real PostGIS test DB, rolled back per test
frontend/
  src/App.tsx                 routes (each guarded by its entry in layout/nav.ts)
  src/layout/                 AppShell, Sidebar, BottomNav, TopBar, nav.ts (menus + roles)
  src/components/ui/          shared UI kit from the mock-up
  src/features/<feature>/     the feature's pages and components
  src/auth/  src/lib/         useAuth, Guarded, api client
docs/                         architecture, conventions, feature docs, decisions, project files
.agents/skills/               the skills above (source of truth)
```

## Commands (from the repo root)

```bash
sh scripts/start.sh                                    # check machine, build, start, wait until up
sh scripts/start.sh --check                            # diagnose only — prints what to fix
docker compose exec backend pytest                     # backend tests
docker compose exec backend ruff check . && docker compose exec backend ruff format .
docker compose exec frontend npm test                  # frontend tests
docker compose exec frontend npm run lint && docker compose exec frontend npm run typecheck
docker compose exec backend alembic revision --autogenerate -m "add boundaries table"
```

App: http://localhost:5173 · API docs: http://localhost:8000/api/docs ·
Demo accounts: `developer@`, `developer2@`, `verifier@`, `staff@`, `buyer@`, `admin@crvr.local` — password `crvr-demo`.
