# 0008 — Host one cheap class demo on Cloud Run + Cloud SQL

**Date:** 2026-11-19 · **Status:** Accepted

## Context

The app must be online for the class presentation and for the professor to test. It is a school
project paid from a team member's own Google Cloud project, so cost matters more than uptime. The
architecture notes planned Cloud Run, Cloud SQL and Cloud Storage; production mode blocked the demo
accounts the professor needs, and the public demo password `crvr-demo` is in the README.

## Decision

- **One environment**, run as production with `DEMO_MODE=true`: demo accounts and sample data are
  seeded, but with a private `DEMO_PASSWORD` (≥ 12 characters, never `crvr-demo`) from Secret
  Manager. The sign-in page does not list the demo accounts (only local development does).
- **One Cloud Run service** serves both the API and the built frontend (`STATIC_DIR`), so the
  browser stays on one origin and the httpOnly cookie needs no CORS. Scales to zero, max 1
  instance, CPU billed only during requests.
- **Cloud SQL `db-f1-micro`** (PostgreSQL 17 + PostGIS), **stopped 23:00–06:00 Bangkok time** by
  Cloud Scheduler, with on/off/hold controls as a script and a GitHub workflow. While it is
  stopped the API answers 503 with a "closed" message.
- **Evidence files** in a private Cloud Storage bucket mounted at `/data/evidence` (no code
  change to F1).
- **Migrations and seeding** run as a Cloud Run job before each rollout, not at container start.
- **GitHub Actions deploys every merge to `main`** after CI, signing in with Workload Identity
  Federation restricted to `main` of this repository — no service-account keys.
- The client IP for the security log is read from `X-Forwarded-For` only as far as the configured
  number of trusted proxies (`FORWARDED_IP_HOPS=1` on Cloud Run).

## Alternatives considered

- **Neon / Supabase free Postgres** — $0, but outside Google Cloud; the team chose Cloud SQL.
- **Separate frontend service (nginx) or Firebase Hosting** — two cold starts and more images;
  Firebase rewrites drop every cookie except `__session`, which would break sign-in.
- **Load balancer for the custom domain** — ~US$18/month; Cloud Run domain mapping is free.
- **Public `crvr-demo` password with one-click sign-in** — anyone finding the URL could act as admin.

## Consequences

- About ฿300–370/month, mostly Cloud SQL. A budget alert at ฿500 e-mails the billing admins.
- The site is "closed" overnight unless someone runs `hold`; the first request after idle is slow.
- Demo data can be wiped and reseeded at any time (Reset demo data workflow) — the hosted
  instance must never hold real registry data.
- Runbook: [docs/deployment.md](../deployment.md).
