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

**Merged** (#3 closed). Developers register a project in a 4-step form, save and resume drafts, upload evidence that is sealed on upload, see
F2's overlap check inline, and submit only a complete draft. Home shows live status for
developers (own) and registry staff/admin (all). Open follow-ups: #20 (write-once Cloud Storage in
production), #21 (real-phone test), #22 (file-content check and virus scan), #45 (personal data in
sealed evidence).

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
9. ✅ Works at 420 px (UI kit + phone-first layout; tap targets and iOS file picker fixed in #73 — not yet checked on a real phone).

## Decisions

- 2026-11-02 — **Evidence is sealed on upload**, not on submission (mock-up wording: "Files are
  sealed on upload"). Simpler and strictly WORM: a wrong file cannot be removed, only followed by
  the right one. Write-once is enforced three times: no update/delete route or service code, the
  file is created with `open("xb")` and `chmod 444`, and a PostgreSQL trigger rejects UPDATE/DELETE
  on `evidence_files`. *(Updated 2026-11-19: the storage layer now enforces the first of those —
  see the storage-backend decision below.)*
- 2026-11-19 — **Evidence storage is a backend behind an interface** (#20, ADR 0009):
  `EVIDENCE_BACKEND=local` writes to the Docker volume in development and in the tests,
  `EVIDENCE_BACKEND=gcs` writes to the production bucket through the Cloud Storage API. The
  interface has `seal`/`open`/`exists` and no update or delete, the bucket write uses
  `if_generation_match=0` (the API's `open("xb")`), and the bucket carries a seven-year retention
  period. An upload is hashed and measured **before** any backend sees it, so a rejected file
  leaves nothing behind — the only approach that works once the retention policy is locked.
- 2026-11-02 — 4 steps: **1 Project details** (mock-up fields) · **2 Additionality** (reasoning
  ≥ 50 chars + proof upload) · **3 Boundary & evidence** (drop zone, sealed list, F2 banner linking
  to `/boundary?project=<id>`) · **4 Review & submit**. Every step change saves the draft.
- 2026-11-02 — A draft needs only a name; `missing_for_submission()` is the single list of what is
  still needed (all fields, additionality proof, ≥ 1 other evidence file, F2 `issuance_blocked()`
  is `None`). The API returns it as `missing`, the form shows it, `/submit` enforces it (422).
- 2026-11-02 — Only **developers** create/edit/submit; admins and registry staff read everything.
  The *Submit* menu item is developer-only. Verifiers may open **submitted** projects that are
  currently assigned to them (narrowed 2026-11-19, WBS 7.1.1). Projects a user may not see answer
  **404**, not 403.
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
| GET | `/api/projects/{id}` | developer (own), verifier (assigned + submitted), registry_staff, admin | `ProjectDetail`: fields, owner, evidence, `missing`, `boundary_blocked`, `can_edit` |
| PUT | `/api/projects/{id}` | developer (own draft) | Save the draft's fields; 409 once submitted |
| POST | `/api/projects/{id}/submit` | developer (own draft) | Submit; 422 "Still needed: …" if incomplete |
| POST | `/api/projects/{id}/evidence` | developer (own draft) | Multipart `file` + `kind` → sealed `EvidenceOut` (sha256, size); 415 bad format, 413 too large |
| GET | `/api/projects/{id}/evidence/{eid}/file` | as GET project | Download the stored bytes |
| POST | `/api/projects/{id}/evidence/{eid}/erasure` | admin | Destroy the file's encryption key so its content can no longer be read (#45). Body: `reason` (≥ 10 chars), optional `replacement_id`. The sealed object and its row stay; downloads then answer 410 |

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
- ~~Content sniffing (magic bytes) and virus scanning for uploads~~ — done in #22.
- Locking the bucket's retention policy (`LOCK_RETENTION=true`) is still a manual step; until
  it is run, production write-once rests on the code alone.
- Evidence keys sit in the database next to the ciphertext, so a backup is as sensitive as
  the evidence. Moving them to Cloud KMS would separate the two (ADR 0010).

## Progress log

### 2026-11-19 · fix/registration-phone-420px (#21)
- Goal: run the 4-step registration and evidence upload at 420 px and fix what it finds.
- Measured in a 420 × 880 viewport, signed in as a developer, through all four steps. No
  horizontal scrolling anywhere, no clipped text, and every card, field and button fits.
- **Fixed — step tabs were 14 px tall.** The four stepper buttons had no vertical padding, so
  the one-line ones were 14 px and "Boundary & evidence" was 29 px because it wrapped. Under
  the 24 px minimum in WCAG 2.5.8 and hard to hit with a thumb. They are now a uniform 45 px.
- **Fixed — the file picker hid the camera on iOS.** `accept` was a list of bare extensions.
  iOS matches it against UTIs, so extensions it does not know (`.gpx`, `.kml`, `.geojson`) can
  grey out every file in the picker and remove "Take Photo". MIME types now lead the list, with
  `image/*` putting the camera back; the extensions stay for the geospatial formats.
- **Fixed — "Draw the boundary" was a 20 px link.** Now a 44 px inline-flex target.
- Test: `src/features/registration/phone.test.tsx`. jsdom has no layout engine, so the tests
  assert the sizing class on each target and the order of the `accept` list rather than pixel
  heights; the measurements are above.
- **Still open: this was an emulated 420 px viewport, not a real device.** What it cannot tell
  us is whether the camera actually opens and returns a usable photo on iOS, whether a GPX file
  can be picked from Files on Android, and how a 50 MB upload behaves on mobile data. Those
  three need a real Android and iPhone — the remaining half of this issue.

### 2026-11-19 · feature/F1-evidence-crypto-erasure (#45)
- Change request: a landowner's sealed land-title scan shows their national ID and home
  address, and they ask for the personal data to be removed. The system is built so that this
  is impossible — write-once in the API, the service, the storage interface, a database trigger
  and the bucket's retention lock.
- Decision (ADR 0010): **encrypt every evidence file with its own key before sealing, and erase
  by destroying the key.** The ciphertext stays in the bucket, the `evidence_files` row is never
  touched, and the ledger keeps the original SHA-256 — so what the file was and what it hashed
  to stay provable while the bytes become unrecoverable.
- Done: `crypto.py` (AES-256-GCM, one key per file); `evidence_keys` (deletable, cascade) and
  `evidence_erasures` (append-only, with its own trigger); admin-only
  `POST /evidence/{eid}/erasure` taking a reason and an optional redacted replacement; downloads
  of an erased file answer 410 with the reason and a pointer to the replacement.
- A redaction is uploaded **first** and linked as the replacement: erasing on its own would take
  the project's evidence with it, and a verifier would find a hole.
- GCM authenticates too, so a ciphertext altered in the bucket now answers 409 instead of
  returning wrong bytes.
- A missing key with no erasure row answers 404, not 410: a key lost by accident is a fault to
  investigate, not a lawful erasure to report.
- Evidence sealed **before** this change is plaintext in storage. The migration gives each such
  file an `evidence_keys` row with `key`/`nonce` NULL, so it still downloads (and "no row" still
  means a lost key). Erasing one stops the app serving it, but its plaintext stays in storage
  until removed there; the ledger entry records `plaintext_in_storage: true`.
- Test: `tests/test_evidence_erasure.py` — 25 tests, including that the write-once rule and the
  ledger survive an erasure, that erasing one file leaves the others readable, and that no new
  route can delete sealed evidence.
- Changed two existing assertions: the sealed object is ciphertext now, so tests that compared
  it to the plaintext compare the download instead.

### 2026-11-19 · feature/F1-evidence-content-scan (#22)
- Goal: stop trusting the file name. Check what the file really is and scan it for malware
  before it is sealed.
- Done: `scanning.py` reads the format from the first bytes (signatures for PDF, JPEG, PNG,
  HEIC, WebP, TIFF, ZIP-based and old Excel files; text formats are checked by decoding) and
  refuses an upload whose content does not match its extension. A `VirusScanner` streams the
  file to clamd over the INSTREAM protocol — spoken directly, so no client library joins the
  dependency list. Both run between weighing and sealing, and both answer 415 with a message
  for the uploader.
- **Fail closed**: when scanning is on and clamd cannot be reached the upload is refused, not
  sealed unchecked. Evidence is permanent, so "we could not check it" must not become "we kept
  it".
- ClamAV is a compose profile (`docker compose --profile scan up -d clamav`) and off by default,
  so `sh scripts/start.sh` stays fast. The image is amd64 only — on Apple Silicon it runs
  emulated (still starts in ~20 s).
- Test: `tests/test_evidence_scanning.py` — 30 tests. The EICAR case runs against a fake clamd
  in a thread that speaks the real protocol, so it needs no container; a second test runs
  against a real clamd and skips when there is none.
- Changed an existing test: `test_accepted_evidence_formats` uploaded `b"evidence bytes"` under
  eight extensions. That is exactly what #22 forbids, so each case now carries a real header.

### 2026-11-19 · feature/F1-evidence-cloud-storage (#20)
- Goal: write production evidence to the Cloud Storage bucket instead of a local volume, without
  weakening write-once.
- Done: `storage.py` with `LocalEvidenceStorage` and `GcsEvidenceStorage` behind an interface that
  has no update or delete; `EVIDENCE_BACKEND` / `EVIDENCE_BUCKET` settings, with a validator that
  refuses `gcs` without a bucket; uploads hashed and measured before a backend is touched;
  downloads streamed through the app for both backends; Cloud Run switched from the gcsfuse mount
  to the API; seven-year retention period on the bucket in `bootstrap.sh`.
- Why the mount went: gcsfuse cannot give an atomic "fail if it exists" write, `chmod 444` means
  nothing on an object store, and deleting a part-written reject fails once retention is locked.
  ADR 0009.
- Test: `tests/test_evidence_storage.py` — 19 tests covering the backend switch, both backends
  (bucket faked, no network), rejected uploads leaving nothing behind, overwrite refused on both,
  and the full upload/download route running on the bucket backend.
- Follow-up: `LOCK_RETENTION=true` has to be run once against the real bucket.

### 2026-11-19 · fix/F1-verifier-assigned-projects
- Fix: any verifier could open any submitted project and download its evidence. `get_project()`
  now also requires the verifier to be the project's current F3 assignee, so the project page and
  evidence downloads answer 404 otherwise. A verifier who is reassigned away loses access.
- Test: `test_verifiers_see_only_submitted_projects_assigned_to_them`.

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

### 2026-11-16 · feature/F4-real-integrations (#23 prerequisite / #40)
- Added the internal F1 service `buyer_evidence_summaries(db, project_id)` and schema
  `BuyerEvidenceSummary`. Each item contains exactly `kind`, `sealed_at` (UTC timestamp) and
  `sha256`. It selects these columns only, ordered by sealing date and evidence ID.
- F4 calls it only after registry credit and buyer project-grant authorization. It is not a new
  public endpoint and does not open project details or original-file downloads to buyers.
- Filenames, file bytes, storage keys, uploader/owner IDs, names, contacts, baseline and
  additionality free text are excluded. A kind/date/hash summary does not mean the original
  file contents have been redacted; originals remain private.
- Real API integration tests upload files whose names/content contain confidential markers,
  issue the project through F3, and prove no such markers or sensitive fields reach buyer/public
  registry responses. This implements the minimal #23 service contract locally for #40.
