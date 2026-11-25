# 5 · Database design

[← Diagrams](README.md)

PostgreSQL 17 + PostGIS · 18 tables · one schema, tables grouped by the feature that owns them.

## Overview

```mermaid
flowchart LR
    U(["users<br/>5 roles"])
    subgraph F1["F1 · Registration"]
        P["projects"] --- EF["evidence_files"] --- EK["evidence_keys"]
        EF --- EE["evidence_erasures"]
    end
    subgraph F2["F2 · Boundary"]
        BD["boundaries<br/>MULTIPOLYGON"] --- OF["overlap_flags"]
    end
    subgraph F3["F3 · Verification"]
        VA["verification_assignments"] --- VR["verification_reports"] --- AP["approvals"]
        VA --- VRA["verification_reassignments"]
    end
    subgraph F4["F4 · Registry"]
        RC["registry_credits"] --- RH["registry_holdings"]
        RC --- RE["registry_evidence"]
        RC --- RCE["registry_credit_events"]
        RPA["registry_project_access"]
    end
    subgraph F5["F5 · Audit"]
        LE["ledger_entries<br/>hash chain"]
        SE["security_events"]
    end

    P --> BD
    P --> VA
    AP --> RC
    P --> RC
    U --> P
    U -.-> LE
```

## Entity–relationship

```mermaid
erDiagram
    users ||--o{ projects : owns
    projects ||--o{ evidence_files : has
    evidence_files ||--o| evidence_keys : "encrypted by"
    evidence_files ||--o| evidence_erasures : "erased by"
    projects ||--o| boundaries : "land"
    projects ||--o{ overlap_flags : "flagged against other project"
    projects ||--o| verification_assignments : "checked by"
    verification_assignments ||--o{ verification_reports : "verifier signs"
    verification_assignments ||--o{ verification_reassignments : "history"
    verification_reports ||--o| approvals : "staff decides"
    approvals ||--o{ registry_credits : "issues"
    projects ||--o{ registry_credits : "source of"
    registry_credits ||--o{ registry_holdings : "units allocated"
    registry_credits ||--o{ registry_evidence : "public proof"
    registry_credits ||--o{ registry_credit_events : "status history"
    users ||--o{ registry_holdings : "buyer holds"
    users ||--o{ registry_project_access : "buyer may see"
    users ||--o{ ledger_entries : "actor"
    users ||--o{ security_events : "actor"

    users {
        int id PK
        string email UK
        string role "developer | verifier | registry_staff | buyer | admin"
        string password_hash "bcrypt"
        bool is_active
    }
    projects {
        int id PK
        string code UK "CRVR-0200"
        int owner_id FK
        string status "draft | submitted | verified | issued"
        string methodology
        int est_removal_tco2e
    }
    evidence_files {
        int id PK
        int project_id FK
        string kind
        string sha256 "fingerprint"
        string storage_key UK
        datetime sealed_at "write-once"
    }
    evidence_keys {
        int evidence_id PK,FK
        bytes key "null = erased"
    }
    evidence_erasures {
        int id PK
        int evidence_id FK
        string reason
    }
    boundaries {
        int id PK
        int project_id FK,UK
        geometry geom "MULTIPOLYGON 4326"
        float area_m2
    }
    overlap_flags {
        int id PK
        int project_id FK
        int other_project_id FK
        float overlap_pct "> 0.5 % blocks"
        string status "open | disputed | resolved | superseded"
    }
    verification_assignments {
        int id PK
        int project_id FK,UK
        int verifier_id FK
        int assigned_by_id FK
        string status
    }
    verification_reports {
        int id PK
        int assignment_id FK
        json checklist
        string decision "sign_off | request_changes"
        string risk_rating "low | medium | high"
    }
    verification_reassignments {
        int id PK
        int assignment_id FK
        int verifier_id FK
    }
    approvals {
        int id PK
        int report_id FK,UK
        int approver_id FK "not verifier, not owner"
        string decision "approved | rejected"
    }
    registry_credits {
        int id PK
        string serial UK "serial range"
        int source_project_id FK
        int source_approval_id FK
        int quantity
        string status "active | buffer | retired"
        string snapshot_sha256
    }
    registry_holdings {
        int id PK
        int credit_id FK
        int buyer_id FK
        int first_unit
        int last_unit
        string status "held | retired"
    }
    registry_evidence {
        int id PK
        int credit_id FK
        bool buyer_visible
    }
    registry_credit_events {
        int id PK
        int credit_id FK
        string action
    }
    registry_project_access {
        string project_reference PK
        int buyer_id PK,FK
    }
    ledger_entries {
        int id PK
        string action
        string entity
        int actor_id FK
        json payload
        string prev_hash
        string hash UK
    }
    security_events {
        int id PK
        string event_type "failed sign-in, 403…"
        int actor_id FK
        string source_ip
    }
```

| Guard | Where |
|---|---|
| Evidence can't be changed | DB trigger on `evidence_files` |
| Ledger can't be edited | DB trigger + `prev_hash → hash` chain |
| Erasure log is append-only | DB trigger on `evidence_erasures` |
| Retired units are locked | DB trigger on `registry_holdings` |
| One boundary / one assignment per project | `UNIQUE (project_id)` |
| Overlap measured in the DB | PostGIS `ST_Intersection` / `ST_Area` on `boundaries.geom` |
