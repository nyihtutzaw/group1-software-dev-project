# F3 — Verification workflow

> Context doc for people and AI agents. Read before working on this feature; update before you stop.
> How: `.agents/skills/write-docs/SKILL.md`.

| | |
|---|---|
| **Owner** | Pyae Phyo Hein (supports: Jingqing) |
| **Issue** | [#5](https://github.com/nyihtutzaw/group1-software-dev-project/issues/5) — requirements and acceptance checklist |
| **Requirements** | Charter §5.3 (structured verification workflow) · FR-10 maker-checker · WBS 7.0 |
| **Code** | `backend/app/features/verification/` · `frontend/src/features/verification/` |
| **Mock-up** | *Verify* (Verification queue + open review) |

## Status

In progress — queue, checklist, maker-checker and issuance are on `main`. This branch
(`fix/F3-review-followups`) records who assigns verifiers, lists real evidence on the baseline
checklist line, lets staff reassign after a rejection or a request for changes, and splits issued
credits into a tradable batch and a non-tradable buffer pool.

## Scope

A work queue of assigned projects with due dates and overdue flags. Opening one gives the verifier
the evidence, the automatic check results and a structured checklist — land title matches
applicant, no boundary overlap, baseline complete, methodology correctly applied. The verifier's
decision is then **approved or rejected by a different member of registry staff** (maker-checker),
so separation of duties is enforced by the system, not by convention.

**Out of scope:** replacing physical site verification.

## Acceptance criteria

From WBS 7.x and the design report:

1. An assigned verifier sees only their projects' evidence (7.1.1).
2. The verifier reviews evidence and automatic checks in one place (7.1.2).
3. The verifier submits a structured verification report (checklist + note) (7.2.1).
4. Registry staff approve or reject with a recorded rationale (7.2.2).
5. The approver can never be the verifier/submitter of the same decision (FR-10).
6. The full verification chain is retrievable per project (7.3.1).
7. Sign-off and approval are written to the audit ledger (with F5).

## Decisions

- 2026-10-27 — Queue is sorted oldest-due first; overdue = past due date (mock-up).
- 2026-11-01 — **Working assumption for this branch:** `registry_staff` and `admin` create
  assignments. Superseded by the decision below.
- 2026-11-19 — **Registry staff and admin assign verifiers** ([ADR 0007](../decisions/0007-who-assigns-verifiers.md),
  issue #28). A verifier cannot. The same two roles may reassign the verifier and due date after
  a rejection or a request for changes (issue #26). The change is a history event and a
  `verification.reassigned` ledger entry.
- 2026-11-19 — **Reversal risk is set on sign-off** (issue #42): low 10%, medium 15%, high 20%.
  Issuance splits the staff-confirmed quantity. The first unit range stays `active` and tradable;
  the remainder is a second batch with status `buffer`, its own serial range, and the same
  approval. Buffer credits cannot be allocated or retired. A rounded buffer of zero (a very small
  batch) issues one tradable batch only. Half-up rounding: `(quantity * percent + 50) // 100`.
- 2026-11-01 — A `verifier` receives only rows where they are `verifier_id`. `registry_staff` and
  `admin` receive every assignment. The API enforces this.
- 2026-11-01 — Overdue means `due_date` is before today (UTC) and the assignment is not approved
  or rejected. The due date itself is not overdue. *(Rejected changed on 2026-11-02, below.)*
- 2026-11-01 — One assignment per project. Sign-off cannot be edited. "Request changes" stores a
  report and sets the assignment to `changes_requested`. The project owner reads the note from
  `GET /api/verifications/notes`. *(Status part superseded on 2026-11-02, below.)*
- 2026-11-01 — Maker-checker: the approver must be `registry_staff` or `admin`, and must not be
  the user who signed off or the project owner. Sign-off and the approval call `record_action()`.
- 2026-11-02 — **F3 moves `projects.status` after submission** (F1 marks `verified` as "set by F3").
  Only a `submitted` project can be assigned (409 otherwise). "Request changes" returns the project
  to `draft` and clears `submitted_at`, because F1 only accepts edits and new evidence on a draft;
  files already sealed stay write-once. The verifier cannot report again until the developer
  resubmits, and the note leaves the developer's Home once they do. Approval sets `verified`.
- 2026-11-02 — **A staff rejection also returns the project to `draft`**, with the rationale shown
  on the developer's Home (`NoteOut.kind` = `rejected`; a verifier's note is `changes_requested`).
  The assignment stays `rejected` but reopens: once the developer resubmits, the same verifier
  reports again and a staff member decides on the new sign-off. One assignment per project is kept;
  the chain shows every round. A rejected assignment still counts against its due date (only
  `approved` is closed).
- 2026-11-02 — Demo seed follows F1's seeded statuses: CRVR-0147 (submitted) is in review and
  overdue; CRVR-0131/0092 (verified) and CRVR-0088 (issued) carry a sign-off plus staff approval.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/verifications/queue` | verifier (own), registry_staff, admin (all) | Queue, oldest due date first, with overdue flag and counts |
| GET | `/api/verifications/verifiers` | registry_staff, admin | Active verifiers for the assign form |
| POST | `/api/verifications/assignments` | registry_staff, admin | Assign a verifier and a due date |
| PATCH | `/api/verifications/assignments/{id}` | registry_staff, admin | Reassign verifier or due date after rejection or request-changes |
| GET | `/api/verifications/assignments/{id}` | assigned verifier, registry_staff, admin | Evidence summary, F2 overlap check, checklist, chain |
| POST | `/api/verifications/assignments/{id}/report` | assigned verifier | Checklist + note: `sign_off` or `request_changes` |
| POST | `/api/verifications/reports/{id}/decision` | registry_staff, admin, not the maker or owner | Approve or reject a sign-off with a rationale |
| POST | `/api/verifications/projects/{id}/issue` | registry_staff, admin (independent of maker/owner) | Explicit post-approval issuance; returns the F4 credit batch (201) |
| GET | `/api/verifications/projects/{id}/chain` | owner, assigned verifier, registry_staff, admin | Full chain for one project |
| GET | `/api/verifications/notes` | developer (own projects) | Latest "request changes" note |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/verify` | verifier, registry_staff, admin | Queue in tabs (In progress · Awaiting approval · Approved), and for staff/admin an Assign verifier tab; each row opens its review |
| `/verify/:id` | verifier, registry_staff, admin | One review: tabs for Review (checklist, note, sign-off or the staff decision), Evidence & checks, and History; summary panel on the side |
| `/` | developer | Verifier note when changes were requested, above the F1 placeholder |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `verification_assignments` | project_id (unique), verifier_id, assigned_by_id, due_date, status | One verifier per project |
| `verification_reports` | assignment_id, verifier_id, checklist JSON, note, decision, risk_rating, signed_at | `risk_rating` is required on sign-off |
| `verification_reassignments` | assignment_id, actor_id, previous verifier and due date, new verifier and due date | One row per staff change |
| `approvals` | report_id (unique), approver_id, decision, rationale, decided_at | One decision per sign-off |
| `registry_credits` | status includes `buffer`; unique `(source_approval_id, status)` | Shared with F4. One tradable batch and one buffer batch per approval |

## Depends on / used by

- Uses: F1 projects + evidence, F2 overlap result, F5 roles + ledger.
- Used by: F4 (only approved projects issue credits).

## Open questions

None for assignment or the buffer split. A later vintage or a second tradable batch from the same
approval is still out of scope (see the 2026-11-16 issuance note).

## Progress log

### 2026-11-01 · feature/F3-assignment-queue
- Goal: an assigned verifier sees only their projects, oldest due date first, with the due date
  and an overdue flag (issue #5: 7.1.1 and the queue checkbox). Evidence review (7.1.2) waits
  until F1 has evidence to show.
- Plan: 1) `verification_assignments` model + migration (`project_id`, `verifier_id`,
  `assigned_by`, `due_date`, `status`) on the F2 `projects` stub 2) assign service — staff and
  admin only — plus tests that verifier A cannot read verifier B's rows 3) replace the
  placeholder `GET /api/verifications/queue` (own rows for a verifier; all rows for staff and
  admin; sort by `due_date` ascending; `overdue` when `due_date` is before today) 4) `/verify`
  queue UI from the mock-up: subtitle counts, Assigned / Overdue tiles, rows with project name,
  code, due date and an `OVERDUE` chip. Signed-off-this-year stays 0 until reports exist.
- Next: step 1, the assignment table. Reports, checklist and maker-checker stay on later branches.

### 2026-11-01 · feature/F3-assignment-queue (workflow)
- Done: assignments, queue, checklist report, maker-checker approval, project chain, developer
  note, demo queue for `verifier@crvr.local`, backend and frontend tests. Ledger writes go through
  `record_action()` (still F5's log stub). Evidence bytes are not listed because F1 has no files yet.
- Next: tick the issue checklist once the PR is reviewed. Ask the team who should assign verifiers.

### 2026-11-02 · feature/F3-assignment-queue (sync with F1)
- Done: rebased on `main` after F1 (#14) merged. The F3 migration now revises F1's
  `47c89f71feec`, so there is one Alembic head. F1's Home dashboard shows `DeveloperNotes` under the
  header. F1's Home tests answer the notes request separately, and a new test covers the note.
  Prettier fixed in `VerifyPage.test.tsx` (CI frontend gate).
- Next: F3 sign-off/approval does not yet move `projects.status` to `verified`; assignment should
  require a `submitted` project; align demo seed with F1's seeded statuses.

### 2026-11-02 · fix/F3-project-status-handoff
- Done: end-to-end check of F1 → F2 → F3 on `main` found the handoffs broken. A draft could be
  assigned; request changes left the project sealed, so the developer could not act on the note;
  approval left it `submitted`; the review still said F1 stores no files; the demo queue showed
  verified/issued projects as waiting. Fixed all five (see Decisions 2026-11-02), with tests.
- Next: decide what follows a rejection (Open questions). Existing local databases keep the old
  demo queue — `sh scripts/start.sh --fresh --yes` reseeds it.

### 2026-11-02 · fix/F3-rejection-returns-to-draft
- Done: a staff rejection no longer strands the project as `submitted`. It goes back to `draft`
  with the rationale on the developer's Home; after resubmission the same assignment is reviewed
  and decided again (see Decisions). Backend test covers the full reject → resubmit → approve round.
- Next: reassigning a verifier / resetting the due date after a rejection (Open questions).

### 2026-11-02 · chore/ui-verify-tabs-registry-detail
- Done: `/verify` was one long column (queue, open review, chain, assign form). The queue now sits
  in tabs grouped by where each assignment is in the maker-checker flow, as a compact table, and
  each row opens `/verify/:id` with its own Review / Evidence & checks / History tabs and a summary
  panel. Staff open on "Awaiting approval" when something is waiting. No API change.

### 2026-11-16 · feature/F4-real-integrations (#25 prerequisite / #39)
- Added `issuance.issue_credits` behind `POST /api/verifications/projects/{id}/issue`.
  A registry staff member/admin explicitly triggers issuance **after** staff approval. Approval
  still sets `verified`; it does not silently turn estimated removal into issued tonnes.
- Request: `{"country":"Thailand","vintage":2026,"quantity":73}`. These are staff-confirmed
  public country and batch values; F1 has no country field and only stores estimated tonnes.
  Vintage must fall in `[crediting_start_year, crediting_end_year)` and cannot be in the future.
  Quantity is a strict positive integer, capped at 1 billion (not copied from the estimate).
- Requires a verified, unissued project, its approved assignment and latest signed-off report,
  an approved staff decision, complete checklist, and independent approver/issuer (neither
  verifier nor project owner). Calls F2 `issuance_blocked()` immediately before issuance.
- Reuses F4 `registry_credits` as the authoritative batch rather than creating a second credits
  table: public snapshot, serial, vintage and quantity plus internal source project/approval FKs.
  Serial format: `<project-code>-<vintage>-A<approval-id:08d>-000000001-<quantity:09d>`.
  The approval ID gives each batch a unique namespace; one batch per approval. A second issue
  request returns 409 with no second credit, history row or issuance entry. Subsequent vintages
  or multiple batches per approval are outside this minimal prerequisite and need their own policy.
- Locks/refetches project and assignment, publishes through existing F4 `publish_credit`, changes
  the project to `issued`, and writes `credit.issued` through the real F5 `record_action`.
  The event contains credit/approval IDs, serial, vintage and quantity. Publication, source links,
  lifecycle event, project status and audit write share one transaction; ledger failure rolls back
  all issuance changes. Existing sign-off/approval APIs and UI remain unchanged.
- Real tests cover registration/upload/boundary/submission → sign-off → approve → issue → public
  registry, repeated issuance, unauthorized roles, invalid states/values, live F2 blocking and
  rollback when audit writing fails. This supplies the minimal #25 prerequisite locally for #39.

### 2026-11-19 · fix/F3-review-followups
- Done: issues #26, #27, #28 and #42. Baseline checklist text counts sealed evidence by kind.
  Staff and admin are the assigners (ADR 0007) and can reassign after a rejection or a request
  for changes; the History tab and `verification.reassigned` record it. Sign-off stores a reversal
  risk rating, and issuance puts that percentage into a `buffer` credit that cannot be allocated
  or retired.
- Next: none on these four issues. F4's public registry already lists the buffer row because
  `CreditOut.status` now includes `buffer`.

### 2026-11-19 · fix/F3-history-keeps-original-assignment
- Fix: after a reassignment, the first History entry ("Assigned to … · due …") showed the new
  verifier and due date, because it read the assignment row, which reassignment updates. It now
  reads the original values from the first reassignment record, so the history no longer changes
  after the fact. The reassignment test checks the original entry.
