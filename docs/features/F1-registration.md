# F1 — Project registration & evidence

> Context doc for people and AI agents. Read before working on this feature; update before you stop.
> How: `.agents/skills/write-docs/SKILL.md`.

| | |
|---|---|
| **Owner** | Jingqing (supports: Zay Yar Phyo, Nyi Htut Zaw) |
| **Issue** | [#3](https://github.com/nyihtutzaw/group1-software-dev-project/issues/3) — requirements and acceptance checklist |
| **Requirements** | FR-01 Project registration · FR-02 Evidence submission · WBS 4.0 |
| **Code** | `backend/app/features/registration/` · `frontend/src/features/registration/` |
| **Mock-up** | *Home* (My projects) and *Submit* (Register a project) |

## Status

Not started — placeholder pages for `/` and `/projects/new`; `GET /api/projects` returns `[]`.

## Scope

A guided multi-step form where a project developer registers a project — identity, methodology,
crediting period, area and baseline — then uploads evidence (land title, survey PDF, geo-tagged
photos). Files are **sealed on submission** and can never be edited or replaced. Developers track
status on a dashboard; registry staff see all submissions. Standardised intake is the precondition
for every other feature.

**Out of scope:** automated additionality decisions, migrating existing projects, the satellite
monitoring alert (deferred — keep the dashboard slot as a placeholder).

## Acceptance criteria

From WBS 4.x and the design report:

1. A developer can submit a complete project; invalid data is rejected with a clear message (4.1.1).
2. Additionality reasoning and its proof upload are captured and stored (4.1.2).
3. PDF, image, spreadsheet, GPS and land-title formats are accepted as evidence (4.2.1).
4. Uploaded evidence is written once: overwrite and delete are blocked (4.2.2).
5. Developers and registry staff see live project status; the dashboard reserves the monitoring-alert slot (4.3.1).
6. A developer sees only their own projects; registry staff see all.
7. Submission is recorded in the audit ledger (with F5).

## Decisions

- 2026-10-28 — **F2 added a minimal `projects` table** (`backend/app/features/registration/models.py`:
  id, code `CRVR-0147`, name, owner_id, status, created_at), a real `GET /api/projects` (developers:
  own, staff/admin: all) and demo projects in `registration/seed.py`. Extend it — keep id, code, name,
  owner_id, created_at (F2 relies on them). Before submitting, call F2's `issuance_blocked()`.

- 2026-10-27 — Multi-step form with 4 steps as in the mock-up ("Step 2 of 4"); exact steps TBD.
- 2026-10-27 — Local evidence storage is a Docker volume at `STORAGE_DIR` (`/data/evidence`);
  production will use a Cloud Storage bucket with a retention lock. Write-once is enforced in the
  service either way.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/projects` | developer (own), registry_staff, admin | List projects (`ProjectOut`: id, code, name, status, created_at) |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/` | all signed-in | My projects (developer) / overview (others) — placeholder |
| `/projects/new` | developer, admin | Registration form — placeholder |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `projects` | code (unique), name, owner_id, status, created_at | minimal stub from F2 — extend with registration fields |
| — | | `evidence_files` to be designed |

## Depends on / used by

- Uses: F2 overlap result (shown inline on the form), F5 ledger + roles.
- Used by: F2 (boundary belongs to a project), F3 (verifies a project), F4 (credits come from projects).

## Open questions

- Which fields are mandatory per methodology?
- Max evidence file size, and which formats exactly?

## Progress log
