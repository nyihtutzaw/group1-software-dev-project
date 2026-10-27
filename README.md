# CRVR — Carbon Removal Verification Registry

A web application that makes carbon-removal credits auditable: developers register projects and
their land boundaries, overlapping land is detected before any credit is issued, independent
verifiers review evidence under a maker-checker control, and buyers can trace every credit back to
the evidence and the verifier behind it — with every critical action sealed in a tamper-evident
ledger.

ITCS514 Software Project Management · Mahidol University · Group 1 · 2026/27.
Design: [docs/project/](docs/project/README.md).

## Quick start

You need **Docker Desktop** and **git** — nothing else.

```bash
git clone https://github.com/nyihtutzaw/group1-software-dev-project.git
cd group1-software-dev-project
docker compose up
```

The first start builds the images (a few minutes). Then open:

| | |
|---|---|
| App | http://localhost:5173 |
| API docs | http://localhost:8000/api/docs |

Sign in with a demo account (password **`crvr-demo`**), or click one on the sign-in page:

| Role | Email |
|---|---|
| Project developer | `developer@crvr.local` |
| Independent verifier | `verifier@crvr.local` |
| Registry staff | `staff@crvr.local` |
| Buyer | `buyer@crvr.local` |
| Registry admin | `admin@crvr.local` |

Stop with `Ctrl+C` (or `docker compose down`). Start in the background with `docker compose up -d`.

## Team and features

| Feature | Owner |
|---|---|
| F1 Project registration & evidence | Jingqing |
| F2 Geospatial boundary & overlap detection | Nyi Htut Zaw |
| F3 Verification workflow | Pyae Phyo Hein |
| F4 Public registry & buyer transparency | Zay Yar Phyo |
| F5 Security & auditability | Put Thitisawat |

Each feature has a context doc in [docs/features/](docs/features/README.md) — read yours first.

## How we work

1. Start from the latest `main` on a branch: `feature/F2-overlap-engine`.
2. Commit small steps with Conventional Commits: `feat(F2): detect overlaps above tolerance`.
3. Keep your feature doc's status, decisions and progress log current.
4. Open a pull request to `main`; CI must pass and one teammate approves; it is squash-merged.

Details: [docs/conventions.md](docs/conventions.md).

**Using an AI agent?** Claude Code, Codex, Cursor and OpenCode all pick up the shared instructions
(`AGENTS.md`) and skills (`.agents/skills/`) automatically — ask it to "start F2" or "commit this".
See [docs/agents.md](docs/agents.md).

## Common commands

```bash
docker compose exec backend pytest               # backend tests
docker compose exec frontend npm test            # frontend tests
docker compose exec backend alembic revision --autogenerate -m "describe change"
docker compose logs -f backend                   # logs
docker compose down -v                           # wipe the database and start fresh
```

More (dependencies, troubleshooting, Windows): [.agents/skills/dev-environment/SKILL.md](.agents/skills/dev-environment/SKILL.md).

## Stack

React 19 + TypeScript + Tailwind CSS 4 (Vite) · FastAPI (Python 3.13) · PostgreSQL 17 + PostGIS ·
Docker Compose · GitHub Actions · Google Cloud Run (planned). Architecture: [docs/architecture.md](docs/architecture.md).
