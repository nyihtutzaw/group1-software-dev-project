# F4 — Public registry & buyer transparency

> Context doc for people and AI agents. Read before working on this feature; update before you stop.
> How: `.agents/skills/write-docs/SKILL.md`.

| | |
|---|---|
| **Owner** | Zay Yar Phyo (also: shared UI kit and responsive layout) |
| **Requirements** | FR-08 Buyer access · WBS 8.0 |
| **Code** | `backend/app/features/registry/` · `frontend/src/features/registry/` |
| **Mock-up** | *Registry* (Public registry + traceability panel) |

## Status

Not started — placeholder page at `/registry` (public, no sign-in); `GET /api/registry/credits`
returns `[]`.

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
| GET | `/api/registry/credits` | public | Issued credits (placeholder) |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/registry` | public + all signed-in | Credit search + traceability — placeholder |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| — | | `credits` (serial range, vintage, project_id, status) to be designed |

## Depends on / used by

- Uses: F1 projects + evidence, F3 approval, F5 ledger (traceability, "Verify authenticity").

## Open questions

- Serial format — `TH-0147-2027-A-00001–08400` as in the mock-up?
- Who issues credits, and is issuance part of F3 approval or a separate step?

## Progress log
