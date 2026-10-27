# Architecture

One Python API behind a single sign-in check, reading and writing one PostgreSQL + PostGIS database
and one evidence store, served to one responsive React web app (desktop down to 420 px phones).
The full design is in `docs/project/CRVR-Project-Design-Report-v0.1.pdf`.

```
 Browser / phone ──HTTPS──▶ React app (Vite)  ──/api──▶  FastAPI (Python)  ──SQL──▶ PostgreSQL + PostGIS
                                                            │                       users, projects, boundaries,
                                                            │                       verifications, credits, ledger
                                                            └──files──▶ evidence store (write-once)
```

## Local development

`docker compose up` starts three containers; source folders are bind-mounted, so edits reload live.

| Service | Image | Port | Notes |
|---|---|---|---|
| `db` | `infra/db/Dockerfile` (postgres:17 + PostGIS 3) | 5432 | Native on Apple Silicon and Intel. `infra/db/init/01-init.sql` enables PostGIS and creates `crvr_test` on first start. |
| `backend` | `backend/Dockerfile` (python:3.13-slim + uv) | 8000 | On start: `alembic upgrade head` → seed demo users → `uvicorn --reload`. venv lives in `/opt/venv`, outside the mount. |
| `frontend` | `frontend/Dockerfile` (node:24-alpine) | 5173 | Vite dev server; proxies `/api` to `backend:8000`. `node_modules` is a container volume. |

The browser only talks to `:5173`, so the session cookie is same-origin and there is no CORS setup.

## Backend

```
app/main.py            FastAPI app, /api router, /api/health, /api/docs
app/core/config.py     Settings from env vars (pydantic-settings)
app/core/db.py         engine, SessionLocal, get_db, Base, TimestampMixin
app/core/security.py   bcrypt hashing, JWT create/decode
app/core/models_registry.py   imports every */models.py for Alembic + tests
app/auth/              User + Role, login/logout/me, get_current_user, require_roles
app/features/<name>/   one package per feature: router, models, schemas, service
app/seed.py            demo users (dev only)
migrations/            Alembic; autogenerate understands PostGIS via geoalchemy2 helpers
tests/                 pytest against crvr_test; each test runs in a rolled-back transaction
```

- Sync SQLAlchemy 2 sessions (simpler than async; enough for this load).
- All routes live under `/api`. Each feature router declares its own prefix.

## Authentication and roles

- `POST /api/auth/login` checks email + bcrypt password and sets `crvr_session`: an HS256 JWT
  (8 h) in an **httpOnly, SameSite=Lax** cookie (`Secure` in production). JavaScript never sees it.
- `get_current_user` reads the cookie → user (401 if missing/invalid/inactive).
  `require_roles(Role.X, …)` → 403 for other roles.
- Five roles (Charter FR-10): `developer`, `verifier`, `registry_staff`, `buyer`, `admin`.
- Frontend: `useAuth()` (TanStack Query on `/api/auth/me`); `layout/nav.ts` lists every page with
  its allowed roles and drives both the menus and the `<Guarded>` route wrapper. **The frontend
  only hides things; the API enforces.**
- Keycloak/Auth0 (named in the design report) can replace the login later without changing
  `require_roles` — see [ADR 0002](decisions/0002-database-backed-authentication.md).

## Frontend

```
src/main.tsx            QueryClient + BrowserRouter
src/App.tsx             routes, each wrapped in <Guarded page="…">
src/layout/             AppShell (sidebar ≥ 880 px, bottom tab bar on phones), TopBar, nav.ts
src/components/ui/      UI kit reproducing the mock-up (Card, Button, Field, Alert, StatusChip, …)
src/features/<name>/    a feature's pages, components, API hooks
src/index.css           design tokens (light + dark) → Tailwind utilities
```

## Data ownership

| Area | Tables (planned) | Owner |
|---|---|---|
| Users & roles | `users` ✅ | F5 |
| Projects & evidence | `projects`, `evidence_files` | F1 |
| Boundaries | `boundaries` (PostGIS geometry) | F2 |
| Verification | `verification_assignments`, `verification_reports`, `approvals` | F3 |
| Credits | `credits` | F4 |
| Audit | `ledger_entries` (hash-chained, append-only) | F5 |

## CI and deployment

- **CI** (`.github/workflows/ci.yml`, every PR and push to main): backend ruff + migrations check +
  pytest against a PostGIS service; frontend lint, typecheck, tests, build; agent-skill stubs in sync.
- **Production (planned)**: backend and frontend as Docker images on Google Cloud Run, Cloud SQL
  for PostgreSQL + PostGIS, Cloud Storage with a retention lock for evidence. Deploy workflow to be
  added once a GCP project exists.
