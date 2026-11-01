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

In progress — queue, structured checklist, sign-off and maker-checker approval work on
`feature/F3-assignment-queue` (PR #13). Evidence file contents still wait on F1: the review shows
the project record and says uploads are not stored yet, plus the F2 overlap check.

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
  assignments. The issue still asks who assigns; both roles already reach the queue route, and
  staff own the later maker-checker step. Change this if the team decides otherwise.
- 2026-11-01 — A `verifier` receives only rows where they are `verifier_id`. `registry_staff` and
  `admin` receive every assignment. The API enforces this.
- 2026-11-01 — Overdue means `due_date` is before today (UTC) and the assignment is not approved
  or rejected. The due date itself is not overdue.
- 2026-11-01 — One assignment per project. Sign-off cannot be edited. "Request changes" stores a
  report and sets the assignment to `changes_requested`; it does not change `projects.status`
  (F1 owns that column). The project owner reads the note from `GET /api/verifications/notes`.
- 2026-11-01 — Maker-checker: the approver must be `registry_staff` or `admin`, and must not be
  the user who signed off or the project owner. Sign-off and the approval call `record_action()`.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/verifications/queue` | verifier (own), registry_staff, admin (all) | Queue, oldest due date first, with overdue flag and counts |
| GET | `/api/verifications/verifiers` | registry_staff, admin | Active verifiers for the assign form |
| POST | `/api/verifications/assignments` | registry_staff, admin | Assign a verifier and a due date |
| GET | `/api/verifications/assignments/{id}` | assigned verifier, registry_staff, admin | Evidence summary, F2 overlap check, checklist, chain |
| POST | `/api/verifications/assignments/{id}/report` | assigned verifier | Checklist + note: `sign_off` or `request_changes` |
| POST | `/api/verifications/reports/{id}/decision` | registry_staff, admin, not the maker or owner | Approve or reject a sign-off with a rationale |
| GET | `/api/verifications/projects/{id}/chain` | owner, assigned verifier, registry_staff, admin | Full chain for one project |
| GET | `/api/verifications/notes` | developer (own projects) | Latest "request changes" note |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/verify` | verifier, registry_staff, admin | Queue, open review, and (staff/admin) the assign form |
| `/` | developer | Verifier note when changes were requested, above the F1 placeholder |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `verification_assignments` | project_id (unique), verifier_id, assigned_by_id, due_date, status | One verifier per project |
| `verification_reports` | assignment_id, verifier_id, checklist JSON, note, decision, signed_at | Sign-off is the last report |
| `approvals` | report_id (unique), approver_id, decision, rationale, decided_at | One decision per sign-off |

## Depends on / used by

- Uses: F1 projects + evidence, F2 overlap result, F5 roles + ledger.
- Used by: F4 (only approved projects issue credits).

## Open questions

- Who assigns verifiers — registry staff, admin, or both? This branch allows both (see Decisions).
- Should "Request changes" also move `projects.status`? It currently only changes the assignment.

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
