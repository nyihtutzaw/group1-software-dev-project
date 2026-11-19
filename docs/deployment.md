# Deployment — hosted class demo on Google Cloud

> Runbook for people and AI agents. **Owner:** Nyi Htut Zaw (lead), Put Thitisawat (helps).
> Decision record: [ADR 0008](decisions/0008-cloud-run-class-demo.md).

There is **one environment**: a public demo for the class presentation and for the professor to
test online. It runs as production (Secure cookie, strong JWT secret, no auto-reload) with
`DEMO_MODE=true`, so the demo accounts and sample data exist — but with a **private** demo
password, not the public `crvr-demo`.

## What runs where

```
push to main ─► CI ─► Deploy workflow (keyless sign-in, main branch only)
                         1. build infra/cloudrun/Dockerfile → Artifact Registry (tag = git SHA)
                         2. start the database if it is stopped
                         3. Cloud Run job "crvr-tasks": alembic upgrade + demo seed
                         4. Cloud Run service "crvr": the new image
                         5. stop the database again if it is closing time

Browser ─► Cloud Run "crvr" (FastAPI: /api/* + the built React app on the same origin)
              ├─► Cloud SQL "crvr-db" (PostgreSQL 17 + PostGIS, db-f1-micro)
              └─► gs://zaw-personal-project-crvr-evidence (mounted at /data/evidence)
Secrets (Secret Manager): crvr-database-url · crvr-jwt-secret · crvr-demo-password
```

| | Setting | Why |
|---|---|---|
| Project / region | `zaw-personal-project` / `asia-southeast1` (Singapore) | nearest to Thailand |
| Cloud Run | 0–1 instances, 1 vCPU, 512 MiB, CPU only during requests | ~free; first visit after idle takes a few seconds |
| Cloud SQL | `db-f1-micro`, 10 GB SSD, 3 backups, deletion protection | the only real cost |
| Overnight | database **stopped 23:00–06:00 Bangkok time** (Cloud Scheduler) | saves ~30% of the database cost |
| Images | keep the newest 3 | stays inside the free 0.5 GB |
| Budget alert | ฿500/month, e-mails at 50/90/100% | alerts only — it does not stop spending |

All names are in `infra/gcp/config.sh`.

## Cost (estimate)

About **฿300–370 / US$9–11 a month**, almost all Cloud SQL (≈ ฿300 running 17 h/day + ≈ ฿70
storage). Cloud Run, the bucket, Artifact Registry, Secret Manager and Scheduler stay within
their free tiers at class-demo traffic. GitHub Actions is free (public repo). A stopped Cloud SQL
instance may still be billed a little for its IP address — check **Billing → Reports** after the
first week.

## Everyday use

| I want to… | GitHub (browser/phone) | Terminal |
|---|---|---|
| Deploy | merge to `main` (or Actions → **Deploy** → Run) | — |
| See if it is on | Actions → **Demo power** → `status` | `sh infra/gcp/power.sh status` |
| Turn the database on now | **Demo power** → `on` | `sh infra/gcp/power.sh on` |
| Turn it off now | **Demo power** → `off` | `sh infra/gcp/power.sh off` |
| Keep it on all night (late demo/grading) | **Demo power** → `hold`, later `auto` | `power.sh hold` / `power.sh auto` |
| Keep it off for days (holidays) | `off`, then `hold` | `power.sh off && power.sh hold` |
| Restore clean sample data | Actions → **Reset demo data**, type `reset` | — |
| Get the demo password | — | `gcloud secrets versions access latest --secret=crvr-demo-password` |

- The 06:00 start also undoes a manual `off`; use `hold` to keep it off.
- While the database is stopped the site still loads but every action shows *"CRVR is closed
  from 23:00 to 06:00 (Bangkok time)…"* (HTTP 503).
- Terminal commands need gcloud signed in as a project member (`gcloud config configurations
  activate <your config>`); the scripts always target `zaw-personal-project` regardless.

## Giving the professor access

Send the URL and the demo password privately (not in GitHub). The sign-in page lists the demo
accounts; clicking one fills in its e-mail and the password is typed by hand. Mention the
23:00–06:00 closed hours, or run `hold` during the grading week.

Changing the password: add a new version of `crvr-demo-password` in Secret Manager, then run
**Reset demo data** (existing accounts keep the password they were created with).

## One-time setup (already done once — for reference or a new project)

1. A Google account that owns a project with billing, and a separate gcloud configuration:
   `gcloud config configurations create crvr && gcloud auth login && gcloud config set project …`
2. Edit `infra/gcp/config.sh` if the project, region or repository differ.
3. `sh infra/gcp/bootstrap.sh` (~10 min, mostly Cloud SQL). Re-runnable.
4. Set the two repository variables it prints (`GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`) with
   `gh variable set …` or GitHub → Settings → Secrets and variables → Actions → Variables.
5. Run Actions → **Deploy**.

No service-account keys exist: GitHub Actions signs in through Workload Identity Federation,
which only trusts workflows running on `main` of `nyihtutzaw/group1-software-dev-project`.

## Custom domain (Namecheap) — optional

1. `gcloud domains verify <domain>` and add the TXT record in Namecheap → Advanced DNS.
2. `gcloud beta run domain-mappings create --service=crvr --domain=app.<domain> --region=asia-southeast1`
3. Namecheap: CNAME `app` → `ghs.googlehosted.com.`; HTTPS certificate follows in 15 min–24 h.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Site says "closed" in the daytime | database starting (wait 2 min) or stopped: **Demo power** → `status` / `on` |
| Deploy fails at "Job crvr-tasks" | Cloud Run → Jobs → crvr-tasks → logs (usually a migration) |
| Deploy fails at sign-in to Google | repository variables missing/wrong, or the run was not on `main` |
| Can't sign in with a demo account | use the private password, not `crvr-demo`; after 5 failures wait 15 min |

## Progress log

### 2026-11-19 · chore/deploy-cloud-run
- Decided with the team lead (Zaw): cheapest setup, one environment with sample data, Cloud SQL
  stopped overnight, private demo password, deploy on every merge to `main`, domain later.
- App: `DEMO_MODE`, private `DEMO_PASSWORD`, `FORWARDED_IP_HOPS` for the real client IP behind
  Cloud Run, FastAPI serves the built frontend (`STATIC_DIR`), 503 when the database is down.
- Infra: production Dockerfile, migrate/seed/reset job, bootstrap/deploy/power scripts, Deploy /
  Demo power / Reset demo data workflows. Production image tested locally against PostGIS.
- Next: run bootstrap, set repository variables, first deploy, buy and map the domain.
