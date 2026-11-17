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

Issues #39 and #40 implemented locally on `feature/F4-real-integrations`, based on main `bb0940f`.
Reuses merged PR #11 and the current registry table, credit page and evidence dialog. Real F3
issuance publishes into the existing F4 batch table; evidence reads F1's safe sealed metadata.
Because #23/#25 were absent on main, this branch includes their minimal service prerequisites
(see F1/F3 docs), which require cross-feature review. No remote issue status was changed.
Verify authenticity now checks the F5 audit ledger (#29). Registry staff manage buyer access on
`/buyer-access` (#30). Buyers can retire allocated credits (#44).

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
- 2026-11-17 — Authenticity is `intact` only when the **whole** ledger chain verifies and exactly one
  sealed issuance entry matches the published batch: a forger who edits the registry row can
  recompute its digest, but not the hash-chained ledger entry. No issuance entry (demo or
  pre-ledger rows) is `not_recorded`, never `intact`. The public response lists only entry
  id/action/time/hash — payloads and actors stay behind the role-restricted ledger API (#29).
- 2026-11-17 — Staff may grant access only to projects with a visible published credit and only to
  active buyer accounts; other roles already have their own permissions. Grants stay keyed by
  project reference, so one grant covers every batch of that project. Each grant/revoke is a
  ledger entry (`entity="user"`, the buyer's id; payload `project_reference` only — no emails).
  The page lives at `/buyer-access`, not under `/registry/…`, so the Registry menu item is not
  highlighted at the same time (#30).
- 2026-11-17 — Retirement (#44) needs credits a buyer *holds*, which did not exist. Holdings are
  contiguous unit ranges of a batch, allocated by registry staff (the registry's record of a
  sale, from the batch's unallocated tail) to an active buyer who already has project access.
  The buyer retires all or part of a range; partial retirement keeps the retired part in the row
  and moves the rest to a new held row, so serial ranges never overlap. A database trigger
  makes retired rows immutable (no update/delete), so they cannot be transferred, resold or
  unretired even by direct SQL. Retiring every unit of a batch sets the batch status `retired`
  with a history event. Retirement records are public (as in other registries); holder
  identities are not. Reporting year may not be in the future. Allocation and retirement are
  ledger entries with `entity="credit"`. No transfer between buyers is built.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/registry/credits?q=&page=1&page_size=20` | public | Search published credits; literal case-insensitive project, reference, serial or country match; newest vintage first |
| GET | `/api/registry/credits/{id}` | public | Public origin, approval and verification references, lifecycle history, explicit monitoring availability |
| GET | `/api/registry/credits/{id}/evidence` | buyer, registry staff, admin | F1 buyer-safe kind/date/SHA-256 metadata; no original uploads |
| GET | `/api/registry/credits/{id}/retirements` | public (buyer grants apply) | Retirement records: unit-range serial, quantity, beneficiary, reason, reporting year, date — never the buyer's identity |
| GET | `/api/registry/credits/{id}/holdings` | buyer, registry staff, admin | Staff: every holding with buyer email and allocated/unallocated/retired totals. Buyer: own holdings only |
| POST | `/api/registry/credits/{id}/holdings` | registry staff, admin | `{buyer_email, quantity}` → 201; allocates the next contiguous unit range to an active buyer who already has project access (409 otherwise); ledger `credit.allocated` |
| POST | `/api/registry/holdings/{id}/retire` | buyer (holder only) | `{quantity, beneficiary, reason, reporting_year}`; partial quantity splits the range; 404 for another buyer's holding, 409 if already retired or batch not active; ledger `credit.retired` |
| GET | `/api/registry/credits/{id}/integrity` | public | Verify the F5 ledger chain and the credit's sealed `credit.issued` entry (`ledger_status` intact/broken/not_recorded, entry id/action/time/hash), plus the publication digest |

List response: `{items, total, page, page_size}`. Default page size 20, maximum 100. Search
maximum 200 characters. Retired and revoked credits remain discoverable with their status.
Authenticated buyers see only project references granted in `registry_project_access` on **all**
endpoints (including direct detail, integrity and evidence requests). Unpermitted and missing IDs
both return 404. An invalid/inactive session returns 401; it never silently becomes anonymous.
Public metadata is intentionally accessible without an account; grants protect evidence access.
No HTTP write routes are exposed for credits; the only write routes manage buyer grants (below).

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/registry/access` | registry staff, admin | All buyer grants with project name and buyer name/email/active flag |
| GET | `/api/registry/access/options` | registry staff, admin | Active buyers and projects with published credits, for the grant form |
| POST | `/api/registry/access` | registry staff, admin | `{project_reference, buyer_id}` → 201; 404 unpublished project, 422 not an active buyer, 409 duplicate; ledger `registry_access.granted` |
| DELETE | `/api/registry/access/{project_reference}/{buyer_id}` | registry staff, admin | 204; 404 if no such grant; ledger `registry_access.revoked` |

Grant routes live in `backend/app/features/registry/access.py` (schemas, service and router in one
module, mounted under `/registry`).

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/registry` | public + all signed-in | Search and a paginated results table; search text and page are kept in the URL |
| `/buyer-access` | registry staff, admin | Grant form (project + buyer) and the current grants with Revoke (confirmation dialog) |
| `/registry/:id` | public + all signed-in | One credit: origin, verification & approval, history, public retirements; Verify authenticity result beside it; the evidence pack opens in a dialog. Staff also see **Holdings** with an allocate form; buyers see **Your credits** with Retire (dialog with permanence warning, quantity, beneficiary, reason, reporting year) |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `registry_credits` | unique serial, project reference/name, country, vintage, quantity, methodology, verifier/approval references, dates, status, digest | Issuance snapshot plus status, source project/approval FKs and explicit `is_demo`; private IDs excluded from responses |
| `registry_credit_events` | credit ID, issued/retired/revoked, timestamp | Public lifecycle history, separate from F5's tamper-evident ledger |
| `registry_holdings` | credit ID, buyer ID, first/last unit, held/retired, allocated at/by, retired at, beneficiary, reason, reporting year | Contiguous unit ranges of a batch held by a buyer (#44). Trigger `registry_holdings_retired_lock` rejects UPDATE/DELETE of retired rows |
| `registry_project_access` | project reference + buyer ID composite key | Explicit buyer grants, default deny |
| `registry_evidence` | credit ID, title, summary, internal source reference, buyer-visible flag | Legacy synthetic demo summaries only; never used as fallback for real credits |

Migration: `20261028_b873ff0f1830_add_registry_publications.py` after `0001`;
`20261117_a8dd7b5de443_add_registry_holdings_and_retirement.py` adds `registry_holdings` and its lock trigger. No F1/F3/F5 tables
are created by F4, and no dependency or lockfile changes are needed.

### Handoff contract for F1/F3/F5

- F3's staff-only `POST /api/verifications/projects/{id}/issue` validates the approved chain and
  F2 gate, then calls the existing F4 `publish_credit`. `registry_credits` is the issued batch;
  list/detail endpoints already read it, so there is no separate registry copy or sync job.
- Additive migration `ea0deeaddd26` (after `a6c41d9e8f20`) adds nullable source project/approval FKs,
  a unique approval constraint, and `is_demo` defaulting false. Existing public fields/history and
  credit IDs remain unchanged. Only the three exact legacy demo serial/reference pairs are
  marked synthetic; no real project/approval links are guessed for old publications.
- Explicit issuance supplies staff-confirmed country, vintage and tonnes; estimates are not
  automatically issued. One batch per approval, deterministic serial range and independent
  maker/checker checks are documented in F3. Source FKs and publisher/developer IDs stay internal.
- Buyer grants in `registry_project_access` continue to filter list/detail/integrity/evidence.
  Real source links do not grant access automatically. Entitlement provisioning remains an
  authorised administrative operation, not buyer self-service.
- For a real credit, F4 authorizes access **before** calling F1
  `buyer_evidence_summaries(db, credit.source_project_id)`. Each item is exactly
  `{kind, sealed_at, sha256}`. The dialog shows these fields, with no filenames, owner/uploader
  IDs, contacts, internal paths, private project text or file download link. No raw bytes are read.
- An old non-demo publication without an explicit source link returns an empty pack. It never
  borrows a project's files by matching a serial/reference and never falls back to legacy text.
- Synthetic demo packs retain `{id, title, summary}` for the existing local demonstration only.
  Demo credits are hidden from every read endpoint outside `APP_ENV=development`, or whenever
  `SEED_DEMO_USERS` is false, including when demo rows remain in the database.
- F3 writes real `credit.issued` entries through F5's hash-chained ledger in the issuance
  transaction. F4's authenticity endpoint finds the credit's entries (`credit.*` actions whose
  payload `credit_id` is this credit, plus any `entity="credit"` entries), runs F5's
  `verify_ledger_chain`, and compares the sealed serial/quantity/vintage/project with the
  published row (#29).
  Monitoring remains deferred.

### Local demonstration

After normal startup and migrations, run from the repository root:

```bash
docker compose exec backend python -m app.features.registry.demo
```

This opt-in command is idempotent and rejects non-development environments or disabled demo
accounts. It creates three clearly labelled synthetic records and reviewed synthetic summaries;
Each credit is marked `is_demo`; only two project grants go to `buyer@crvr.local`. The third remains publicly discoverable but is
not accessible to that signed-in buyer. One credit is retired to demonstrate history. Nothing
seeds on normal startup. These are fictional demo credits and approvals, never real issuance.

## Depends on / used by

- Uses: F1 projects + evidence, F3 approval, F5 ledger (traceability, "Verify authenticity").

## Open questions

- #44 impact analysis and decision on the change request are still for the owner/team to record
  on the issue; this branch implements the minimal holdings model described above.
- Buffer credits (#42) are not built. When they are, allocation and retirement must refuse
  buffer batches (`holdings.py` notes this).
- Revoking a buyer's project access hides their holdings and the retire action with the credit;
  their retired records stay public. Decide whether holders keep access automatically.
- Cross-feature review of the minimal #23/#25 prerequisites included on this local branch.
- Multiple issuance batches or vintages per approval require a separate issuance policy.
- `verify_ledger_chain` walks the whole ledger on each public authenticity check; fine at
  class-project scale, but a cached chain checkpoint is needed if the ledger grows large.

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

### 2026-11-02 · chore/ui-verify-tabs-registry-detail
- Done: traceability no longer opens under the results list. Each result links to `/registry/:id`
  (origin, verification & approval, history, with the authenticity check beside them) and the
  evidence pack opens in a dialog. Search and page live in the URL, so Back returns to the same
  results. No API change.

### 2026-11-16 · feature/F4-real-integrations
- Goal: #39 real F3-issued credits and #40 F1 buyer-safe evidence summaries, reusing PR #11 and
  the current `/registry/:id` detail/dialog implementation on main at `bb0940f`.
- Dependency inspection: PR #11 is merged. #23 and #25 remain open with no implementing open PR.
  F3 `decide()` moves projects only to `verified`; no credit batch or issuance operation exists.
  F1 stores real sealed evidence but has no buyer-safe summary service.
- Plan: establish the Docker test baseline; preserve F4 API/UI and buyer grant enforcement;
  implement available integration steps and privacy tests; document any unresolved upstream
  contracts rather than treating approved projects as issued credits.
- Delivery: local branch/commits and a prepared PR description only. No push, PR creation, merge,
  issue updates or environment publication without the user's explicit approval.

- Implemented #39: real F3 staff issuance uses the existing F4 batch and read endpoints, explicit
  internal source links, unique approval protection, local-only demo visibility and legacy backfill.
- Implemented #40: the existing evidence dialog consumes the real F1 per-project safe service;
  buyer grant checks precede retrieval and sensitive metadata/raw bytes are excluded.
- Cross-feature code changes: F1 safe summary schema/service; F3 explicit issuance schema/service/
  route. No new dependencies or shared core/auth/UI-kit/layout changes.
- Validation: 221 backend tests and 66 frontend tests passed, backend lint/format/schema drift,
  frontend lint/format/typecheck/production build, and fresh database migration/legacy backfill/
  downgrade/reapply checks. One existing Starlette/httpx deprecation warning remains.
- Environment: built repository images with a local CA-secret override; the restored old database
  has a stale pre-F2 schema. Preserved its volumes and used a separate `crvr-f4-integration` stack
  with fresh volumes to verify the complete current migration chain without altering old data.
- Live browser validation: created a clearly labelled synthetic smoke-test project through real
  F1/F2/F3 APIs (not the registry demo seed), issued it, and opened `/registry/1`. Guest evidence
  access is disabled; the granted local buyer sees only kind/date/full SHA-256. Checked 1280 px
  desktop and 420 px mobile in light/dark themes, no page/dialog horizontal overflow, and no
  confidential filename/content in the dialog. Test data lives only in the isolated local stack.
- Review preparation: local commits only; no push, PR creation, merge, GitHub issue mutation or
  environment configuration/publication performed. PR text saved outside the checkout for review.

### 2026-11-17 · feature/F4-ledger-authenticity
- Goal: #29 — "Verify authenticity" checks the credit's ledger entries and hash chain.
- Done: `service.check_authenticity` uses F5's `verify_ledger_chain` and the sealed
  `credit.issued` payload; `/integrity` returns `ledger_status` + entry hashes; the credit page
  shows intact / failed / not recorded with each entry's full hash. Removed the stale
  `ledger_status: not_available` field from the detail response.
- Tests: real approve → issue → intact; tampered payload, tampered `prev_hash`, tampered earlier
  entry and a forged registry row (digest recomputed) all report broken; other credits'
  entries are ignored; frontend intact/broken/not-recorded/snapshot-mismatch states.
### 2026-11-17 · feature/F4-buyer-access-admin
- Goal: #30 — a screen for staff to grant and revoke buyers' project access.
- Done: `registry/access.py` (list/options/grant/revoke, `require_roles(registry_staff, admin)`,
  `record_action()` for each change); `/buyer-access` page with grant form, grant list and
  revoke confirmation; `Access` menu item for registry staff and admins.
- Tests: grant → buyer sees the credit and evidence on the next request → revoke → 404 again,
  with both ledger entries and an intact chain (staff and admin); developer/verifier/buyer 403,
  anonymous 401, inactive staff 401; validation (unpublished project, non-buyer, inactive buyer,
  duplicate, missing grant) writes nothing to the ledger; frontend grant/refusal/revoke/empty/
  error states and nav roles.
### 2026-11-17 · feature/F4-credit-retirement
- Goal: #44 — buyers retire credits they hold, permanently, with beneficiary, reason and
  reporting year.
- Done: `registry_holdings` table + migration with retired-row lock trigger;
  `registry/holdings.py` (allocate, list, retire, public retirements); credit page sections
  *Retirements* (public), *Holdings* (staff, allocate form) and *Your credits* (buyer, retire
  dialog).
- Tests: allocation ranges and per-buyer visibility; partial retirement splits and is public
  without buyer identity; retired rows cannot be updated/deleted (trigger); retiring every unit
  retires the batch; allocation/retirement role and validation rules; revoked batches; ledger
  entries and intact chain; frontend public/buyer/staff/developer states.
- Live check: demo credit, staff allocated 100, buyer retired 30 → split 1–30 retired /
  31–100 held, public record shown, direct SQL UPDATE of the retired row rejected.
