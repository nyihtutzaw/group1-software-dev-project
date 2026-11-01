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

In progress — assignment queue planned on `feature/F3-assignment-queue`. The page at `/verify` and
`GET /api/verifications/queue` are still placeholders (the queue returns `[]`).

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
  `admin` receive every assignment, so they can see what they assigned before the approval
  screens exist. The API enforces this; the page only hides other people's work.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/verifications/queue` | verifier, registry_staff, admin | Verifier's queue (placeholder) |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/verify` | verifier, registry_staff, admin | Queue + open review — placeholder |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| — | | `verification_assignments`, `verification_reports`, `approvals` to be designed |

## Depends on / used by

- Uses: F1 projects + evidence, F2 overlap result, F5 roles + ledger.
- Used by: F4 (only approved projects issue credits).

## Open questions

- Who assigns verifiers — registry staff, admin, or both? This branch assumes both (see Decisions).
- What does "Request changes" do to the project's status? Out of scope for the assignment-queue branch.

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
