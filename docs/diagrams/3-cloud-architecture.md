# 3 · Cloud architecture

[← Diagrams](README.md)

```mermaid
flowchart LR
    U["🌐 Browser / phone"] -- "HTTPS<br/>crvr.zaw27.com" --> RUN

    subgraph GCP["Google Cloud · Singapore (asia-southeast1)"]
        RUN["Cloud Run service 'crvr'<br/>FastAPI /api/*<br/>+ built React app<br/><i>one origin, scales to zero, max 1</i>"]
        SQL[("Cloud SQL<br/>PostgreSQL 17 + PostGIS<br/>db-f1-micro")]
        GCS[("Cloud Storage<br/>evidence files<br/>private, write-once")]
        SM["🔑 Secret Manager<br/>DB URL · JWT secret<br/>demo password · AI key"]
        SCH["⏰ Cloud Scheduler<br/>DB off 23:00–06:00"]
        AR["📦 Artifact Registry<br/>one image per commit"]
        JOB["Cloud Run job 'crvr-tasks'<br/>migrate + seed"]
    end

    RUN --> SQL
    RUN --> GCS
    SM -.-> RUN
    SCH -.-> SQL
    AR -.-> RUN
    AR -.-> JOB
    JOB --> SQL
    RUN -- "Assistant only" --> OR["OpenRouter (AI)"]
```

| Choice | Why |
|---|---|
| One service for API + frontend | same origin → httpOnly cookie, no CORS, one cold start |
| Scale to zero, DB off at night | ≈ ฿300–370 / month, budget alert at ฿500 |
| Domain mapping, no load balancer | free (a load balancer is ~US$18 / month) |
| Evidence in Cloud Storage API | atomic write-once (a mounted folder can't guarantee it) |

Details: [deployment.md](../deployment.md) · [ADR 0008](../decisions/0008-cloud-run-class-demo.md).
