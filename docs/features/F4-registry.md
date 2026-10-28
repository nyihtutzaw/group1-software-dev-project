# F4 — Public registry & buyer transparency

> Context doc for people and AI agents. Read before working on this feature; update before you stop.
> How: `.agents/skills/write-docs/SKILL.md`.

| | |
|---|---|
| **Owner** | Zay Yar Phyo (also: shared UI kit and responsive layout) |
| **Issue** | [#6](https://github.com/nyihtutzaw/group1-software-dev-project/issues/6) — requirements and acceptance checklist |
| **Requirements** | FR-08 Buyer access · WBS 8.0 |
| **Code** | `backend/app/features/registry/` · `frontend/src/features/registry/` |
| **Mock-up** | *Registry* (Public registry + traceability panel) |

## Status

In progress — F4's persisted read model, API and responsive UI are implemented and tested.
Public search, buyer project grants, reviewed evidence summaries and credit lifecycle history
work. Integration with real F1 evidence, F3 approval/issuance and the F5 audit ledger remains
blocked by those features being placeholders. No automatic issuance or ledger authenticity claim.

## Scope

A searchable registry of issued credits. Selecting one shows its full traceability — serial,
vintage, project, verifier, sign-off date, status (and the monitoring row as a placeholder) — and
gives controlled access to the underlying evidence, filtered by the viewer's role. This is the view
the paused buyers will judge the registry on.

**Out of scope:** monitoring history (satellite monitoring is deferred — show the row as
"not available").

## Acceptance criteria

From WBS 8.x and the design report:

1. Anyone can search issued credits by project, serial or country without signing in.
2. An authorised buyer signs in and sees permitted projects only (8.1.1).
3. A buyer sees verification status and permitted evidence (8.1.2).
4. A buyer traces origin → evidence → verification → credit → audit (8.2.1, Week 14 requirement).
5. Credit history is shown; the monitoring panel shows the reserved placeholder (8.2.2).
6. Developer-sensitive fields are never returned to buyer accounts (8.3.1).

## Decisions

- 2026-10-27 — The registry list is public (no sign-in); evidence packs require a buyer account.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/registry/credits?q=&page=1&page_size=20` | public | Search published credits; literal case-insensitive project, reference, serial or country match; newest vintage first |
| GET | `/api/registry/credits/{id}` | public | Public origin, approval and verification references, lifecycle history, explicit monitoring/ledger availability |
| GET | `/api/registry/credits/{id}/evidence` | buyer, registry staff, admin | Reviewed buyer-safe evidence summaries; no original uploads |
| GET | `/api/registry/credits/{id}/integrity` | public | Compare public publication fields with stored SHA-256 digest; **not** independent ledger verification |

List response: `{items, total, page, page_size}`. Default page size 20, maximum 100. Search
maximum 200 characters. Retired and revoked credits remain discoverable with their status.
Authenticated buyers see only project references granted in `registry_project_access` on **all**
endpoints (including direct detail, integrity and evidence requests). Unpermitted and missing IDs
both return 404. An invalid/inactive session returns 401; it never silently becomes anonymous.
Public metadata is intentionally accessible without an account; grants protect evidence access.
No HTTP write routes are exposed.

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/registry` | public + all signed-in | Search, paginated credit cards, selectable traceability, evidence and integrity results, history |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `registry_credits` | unique serial, project reference/name, country, vintage, quantity, methodology, verifier/approval references, dates, status, digest | Immutable issuance snapshot plus lifecycle status; private developer/publisher user IDs excluded from API schemas |
| `registry_credit_events` | credit ID, issued/retired/revoked, timestamp | Public lifecycle history, separate from F5's tamper-evident ledger |
| `registry_project_access` | project reference + buyer ID composite key | Explicit buyer grants, default deny |
| `registry_evidence` | credit ID, title, summary, internal source reference, buyer-visible flag | Default hidden; only reviewed/redacted buyer-safe summaries may be marked visible |

Migration: `20261028_b873ff0f1830_add_registry_publications.py` after `0001`. No F1/F3/F5 tables
are created by F4, and no dependency or lockfile changes are needed.

### Handoff contract for F1/F3/F5

- F3 calls `registry.service.publish_credit(db, data=PublicationIn(...), developer=..., actor=...)`
  **only after** validating the source approval, approved quantity, serial allocation and full
  maker/checker chain. F4 additionally requires active staff/admin, an independent developer,
  timezone-aware sign-off before issuance, non-future issuance and a unique serial. The caller
  commits the surrounding transaction so issuance and registry publication can be atomic.
- The serial is opaque. F4 does not allocate serial ranges or independently establish approval.
  `verification_status=approved` describes the trusted publication contract, not a live F3 lookup.
- F3 calls `change_status` for active → retired/revoked. It locks the credit, rejects repeat/terminal
  transitions and appends history in the same transaction. The caller commits.
- Authorised provisioning code adds `RegistryProjectAccess` for a buyer and a project reference.
  There is no self-service grant endpoint; F5/admin integration must manage real entitlements.
- F1 must review and redact text **before** adding a buyer-visible `RegistryEvidence` summary.
  This is an explicit allowlist, not automatic PII detection. Unreviewed rows default hidden.
  F4 never reads original files or exposes internal source references, contacts or storage paths.
  Only public-safe project/verifier names and references may be handed to `PublicationIn`.
- F5 must supply a real ledger reference and verification implementation before audit authenticity
  can be shown. Current digest checks only compare publication fields with a co-stored digest;
  they do not cover lifecycle history, replace a signature or prove origin. Both API and UI state
  that independent ledger verification is unavailable. Monitoring remains deferred.

### Local demonstration

After normal startup and migrations, run from the repository root:

```bash
docker compose exec backend python -m app.features.registry.demo
```

This opt-in command is idempotent and rejects non-development environments or disabled demo
accounts. It creates three clearly labelled synthetic records and reviewed synthetic summaries;
only two project grants go to `buyer@crvr.local`. The third remains publicly discoverable but is
not accessible to that signed-in buyer. One credit is retired to demonstrate history. Nothing
seeds on normal startup. These are fictional demo credits and approvals, never real issuance.

## Depends on / used by

- Uses: F1 projects + evidence, F3 approval, F5 ledger (traceability, "Verify authenticity").

## Open questions

- F3 must choose the actual issuance entry point and serial allocator, then call the trusted handoff.
- F1 must supply reviewed summaries from real evidence; originals remain outside this API.
- F5 must integrate entitlement administration and independent ledger authenticity verification.

## Progress log

### 2026-10-28 · feature/F4-public-registry
- Goal: implement F4 acceptance criteria using persisted, explicitly published registry records.
- Plan: 1) publication models + migration 2) public search/detail and buyer evidence authorization
  3) responsive registry and traceability UI 4) database/API/UI tests and integration notes.
- Dependencies: F1, F3 and F5 are placeholders. F4 will expose a trusted publication service, not
  a public issuance API or fabricated verification/ledger data. Evidence packs contain only
  explicitly approved summaries, never raw source files or private developer fields.
- Environment: original database image build needs blocked apt.postgresql.org; use the PostGIS
  project PostgreSQL 17 image for real database validation if available. GitHub issue API blocked;
  use the acceptance criteria recorded above.

- Implemented: four publication/access/history tables and reversible migration; public search,
  pagination and detail; grant-filtered evidence; safe response schemas; snapshot digest check
  with explicit ledger limitation; trusted publication/status services; opt-in synthetic demo.
- UI: shared design tokens and kit, loading/empty/error/retry states, search, pagination, selectable
  traceability, reviewed evidence, integrity warnings and credit history. Session-scoped query keys
  prevent buyer/public caches sharing results. `App.test.tsx` also mocks the new list request.
- Validation: 33 backend tests passed on PostgreSQL 17 + PostGIS (including 21 F4 cases);
  20 frontend tests passed (12 F4 cases); backend lint/format, frontend lint/format/typecheck/build,
  and Alembic model/schema check passed. One pre-existing Starlette/httpx deprecation warning.
- Environment: tested using a local Compose image/init-directory override with the PostGIS
  project's `postgis/postgis:17-3.5`, because apt.postgresql.org remains denied and checkout init
  permissions are private. Tracked infrastructure and dependency files were left unchanged.
- Live validation: Chromium at 1280 px and 420 px; three public demo records versus two buyer
  records, permitted evidence and snapshot check succeed, unpermitted direct evidence returns
  404, `/api/health` succeeds through Vite, and no mobile horizontal overflow. Reviewed screenshots
  against the HTML mock-up and corrected search/pagination button sizing inside F4 only.
- Migration downgrade to `0001`, upgrade to head and schema check passed on the isolated test DB.
- Lifecycle transition refreshes loaded ORM state under its row lock before checking terminal
  status, so an already-loaded active snapshot cannot overwrite another completed transition.
