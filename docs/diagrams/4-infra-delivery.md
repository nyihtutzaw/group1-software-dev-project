# 4 · Infrastructure & delivery

[← Diagrams](README.md)

## From laptop to cloud

```mermaid
flowchart LR
    subgraph Laptop["💻 Each of 5 laptops: only Docker + git"]
        direction TB
        S["sh scripts/start.sh"] --> DC["Docker Compose"]
        DC --> FE["frontend :5173<br/>Vite + React"]
        DC --> BE["backend :8000<br/>FastAPI"]
        DC --> DB[("db :5432<br/>PostgreSQL + PostGIS")]
    end

    subgraph GH["GitHub"]
        direction TB
        PR["Pull request<br/>a teammate reviews"] --> CI["CI<br/>lint · tests · build"]
        CI --> MG["Merge to main<br/>only with green CI"]
        MG --> DEP["Deploy workflow<br/>keyless sign-in to Google<br/>(Workload Identity)"]
    end

    subgraph GC["Google Cloud"]
        direction TB
        AR["Artifact Registry<br/>image tagged by commit"] --> JOB["Cloud Run job<br/>migrate + seed"]
        JOB --> RUN["Cloud Run 'crvr'<br/>crvr.zaw27.com"]
    end

    Laptop -- "git push" --> PR
    DEP --> AR
```

## What CI checks

```mermaid
flowchart LR
    P["push / PR"] --> B["backend<br/>ruff · migrations · pytest<br/>on real PostGIS"]
    P --> F["frontend<br/>eslint · prettier · tsc · vitest · build"]
    P --> A["agent-skills<br/>stubs in sync"]
    B & F & A --> D{"on main?"}
    D -- yes --> DEP["deploy (~3 min)"]
    D -- no --> X["done: ready for review"]
```

## Ops buttons (GitHub Actions)

| Workflow | Does |
|---|---|
| `ci.yml` → `deploy.yml` | every merge to `main` goes live |
| `demo-power.yml` | database on / off / hold (e.g. grading week) |
| `reset-demo.yml` | wipe and reseed demo data before a presentation |
