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

**Built, ready for review** on `feature/F1-project-registration` (closes #3). Developers register a
project in a 4-step form, save and resume drafts, upload evidence that is sealed on upload, see
F2's overlap check inline, and submit only a complete draft. Home shows live status for
developers (own) and registry staff/admin (all).

## Scope

A guided multi-step form where a project developer registers a project — identity, methodology,
crediting period, area and baseline — then uploads evidence (land title, survey PDF, geo-tagged
photos). Files are **sealed on upload** and can never be edited or replaced. Developers track
status on a dashboard; registry staff see all submissions. Standardised intake is the precondition
for every other feature.

**Out of scope:** automated additionality decisions, migrating existing projects, the satellite
monitoring alert (deferred — keep the dashboard slot as a placeholder).

## Acceptance criteria

From WBS 4.x and the design report:

1. ✅ A developer can submit a complete project; invalid data is rejected with a clear message (4.1.1).
2. ✅ Additionality reasoning and its proof upload are captured and stored (4.1.2).
3. ✅ PDF, image, spreadsheet, GPS and land-title formats are accepted as evidence (4.2.1).
4. ✅ Uploaded evidence is written once: overwrite and delete are blocked (4.2.2).
5. ✅ Developers and registry staff see live project status; the dashboard reserves the monitoring-alert slot (4.3.1).
6. ✅ A developer sees only their own projects; registry staff see all.
7. ✅ Drafts can be saved and resumed; only a complete draft can be submitted.
8. ✅ Submission and evidence sealing go through `record_action()` (F5 stub logs only until F5 lands).
9. ✅ Works at 420 px (UI kit + phone-first layout; not yet checked in a real phone browser).

## Decisions

- 2026-11-02 — **Evidence is sealed on upload**, not on submission (mock-up wording: "Files are
  sealed on upload"). Simpler and strictly WORM: a wrong file cannot be removed, only followed by
  the right one. Write-once is enforced three times: no update/delete route or service code, the
  file is created with `open("xb")` and `chmod 444`, and a PostgreSQL trigger rejects UPDATE/DELETE
  on `evidence_files`.
- 2026-11-02 — 4 steps: **1 Project details** (mock-up fields) · **2 Additionality** (reasoning
  ≥ 50 chars + proof upload) · **3 Boundary & evidence** (drop zone, sealed list, F2 banner linking
  to `/boundary?project=<id>`) · **4 Review & submit**. Every step change saves the draft.
- 2026-11-02 — A draft needs only a name; `missing_for_submission()` is the single list of what is
  still needed (all fields, additionality proof, ≥ 1 other evidence file, F2 `issuance_blocked()`
  is `None`). The API returns it as `missing`, the form shows it, `/submit` enforces it (422).
- 2026-11-02 — Only **developers** create/edit/submit; admins and registry staff read everything.
  The *Submit* menu item is developer-only. Verifiers may open **submitted** projects (F3 will
  narrow to assignments). Projects a user may not see answer **404**, not 403.
- 2026-11-02 — After submission F3 moves the status (see F3 doc): a verifier's "request changes"
  returns the project to `draft` (and clears `submitted_at`) so the developer can edit, add
  evidence and resubmit; staff approval sets `verified`.
- 2026-11-02 — Crediting period stored as start/end **years** (2000–2200, end > start, ≤ 100 y);
  methodologies VM0047, VM0042, ACM0003, VM0033. New codes from sequence `project_code_seq`
  (CRVR-0200 onwards; below is demo data).
- 2026-11-02 — Formats: PDF; JPG/PNG/HEIC/WebP/TIFF; XLSX/XLS/ODS/CSV; GPX/KML/KMZ/GeoJSON; ZIP.
  Checked by extension; max `EVIDENCE_MAX_BYTES` (50 MB). SHA-256 computed while streaming to disk.
- 2026-11-02 — Status chip: an open/disputed F2 overlap shows **OVERLAP** over the workflow status;
  progress bar draft 1 · submitted 2 · verified 3 · issued 4.
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
| GET | `/api/projects` | developer (own), registry_staff, admin | List (`ProjectOut`: id, code, name, status, methodology, area_ha, est_removal_tco2e, submitted_at, evidence_count, overlap) |
| POST | `/api/projects` | developer | Start a draft (`ProjectIn`, only `name` required) → `ProjectDetail` 201 |
| GET | `/api/projects/{id}` | developer (own), verifier (submitted), registry_staff, admin | `ProjectDetail`: fields, owner, evidence, `missing`, `boundary_blocked`, `can_edit` |
| PUT | `/api/projects/{id}` | developer (own draft) | Save the draft's fields; 409 once submitted |
| POST | `/api/projects/{id}/submit` | developer (own draft) | Submit; 422 "Still needed: …" if incomplete |
| POST | `/api/projects/{id}/evidence` | developer (own draft) | Multipart `file` + `kind` → sealed `EvidenceOut` (sha256, size); 415 bad format, 413 too large |
| GET | `/api/projects/{id}/evidence/{eid}/file` | as GET project | Download the stored bytes |

No PUT/PATCH/DELETE exists for evidence. Ledger actions via `record_action()`: `project.created`,
`evidence.sealed` (payload: sha256, size, kind), `project.submitted` (payload: all evidence hashes).

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/` | all signed-in | Developer: *My projects* (tiles, rows, monitoring slot). Staff/admin: *All projects*. Verifier/buyer: pointer to their page |
| `/projects/new` | developer | Step 1 of the registration form; creates the draft |
| `/projects/:id/edit?step=1…4` | developer | Resume a draft; non-editable projects redirect to the project page |
| `/projects/:id` | developer (own), verifier, registry_staff, admin | Read-only project: status, details, additionality, sealed evidence, boundary check |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `projects` | code (unique), name, owner_id, status, methodology, crediting_start_year, crediting_end_year, area_ha, est_removal_tco2e, baseline_summary, additionality_reasoning, created_at, updated_at, submitted_at | registration fields nullable (drafts); `status` is a plain string so F3/F4 can add states |
| `evidence_files` | project_id, kind, filename, content_type, size_bytes, sha256, storage_key (unique), uploaded_by_id, sealed_at | write-once trigger `evidence_files_write_once` |

Migration: `20261102_47c89f71feec_add_registration_fields_and_evidence.py` (also creates
`project_code_seq`). Files live at `STORAGE_DIR/<project_id>/<uuid><ext>`.

## Depends on / used by

- Uses: F2 overlap result (shown inline on the form), F5 ledger + roles.
- Used by: F2 (boundary belongs to a project), F3 (verifies a project), F4 (credits come from projects).

## Open questions

- Which fields are mandatory per methodology? (Today: the same set for all.)
- Should evidence be allowed after submission (e.g. a verifier asks for more)? Today: drafts only.
- Content sniffing (magic bytes) and virus scanning for uploads — extension check only for now.

## Progress log

### 2026-11-02 · feature/F1-project-registration
- Goal: all acceptance criteria of issue #3 on one branch — draft → submit registration with
  additionality, write-once evidence, dashboard with live status.
- Plan:
  1. Extend `projects` (methodology, crediting period, area, est. removal, baseline,
     additionality, submitted_at) + `evidence_files` table with a write-once DB trigger.
  2. Service + API: create/update draft, upload/list/download evidence (no update/delete path),
     submit with completeness check and F2 `issuance_blocked()`; ledger via `record_action()`.
  3. Backend tests for every criterion and role rule.
  4. Home dashboard: stat tiles, project rows (mini map, progress, status chip), monitoring slot.
  5. 4-step registration form (details · additionality · boundary & evidence · review & submit)
     and a project detail page.
  6. Frontend tests, doc update, PR.
- Done (2026-11-02): all plan steps. Backend: 41 new tests (formats, write-once API + DB trigger,
  validation, submission rules, F2 overlap gate, visibility per role). Frontend: 14 new tests
  (dashboard per role, form validation, draft save, uploads, missing list, submit). Checked the
  whole flow end to end against the running stack (create → upload → boundary → submit; files
  are read-only on the volume, DELETE refused, download returns the exact bytes).
- Shared code touched: `core/config.py` (`EVIDENCE_MAX_BYTES`), `lib/api.ts` (validation messages),
  `App.tsx` (routes), `layout/nav.ts` (Submit developer-only).
- Browser check (headless Chrome, 1280 px and 390 px, against the mock-up): home, all four form
  steps and the project page render without console errors. Fixed two things it found: the
  crediting-period year inputs overflowed the card (`cn()` does not merge Tailwind classes, so the
  kit's `w-full` won), and dates read "12 Sept" in newer browsers instead of the mock-up's "12 Sep".
- Next: F5 replaces the `record_action()` stub; F3 moves `submitted` projects on and may narrow
  verifier access; check the form on a real phone.
