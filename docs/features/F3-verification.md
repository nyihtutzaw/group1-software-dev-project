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

Not started — placeholder page at `/verify`; `GET /api/verifications/queue` returns `[]`.

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

- Who assigns verifiers — registry staff or admin?
- What does "Request changes" do to the project's status?

## Progress log
