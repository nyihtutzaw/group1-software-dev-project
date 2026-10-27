---
name: write-docs
description: Keep CRVR's markdown docs useful as shared context for people and AI agents — update the feature context doc (status, decisions, API, pages, progress log), add decision records, and keep architecture notes current. Use at the start and end of every work session, after any design decision, and when adding endpoints or pages.
---

# Write docs

Docs are the team's shared memory. Five people and several AI tools work on this repo; none of them
remember the last session. **If it is not in the docs, the next agent will not know it.**

## What lives where

| Doc | Purpose | Update when |
|---|---|---|
| `docs/features/F<n>-*.md` | One per feature: scope, acceptance criteria, status, decisions, API, pages, progress log | Every session on that feature |
| `docs/architecture.md` | How the system fits together | A shared piece changes (auth, DB, deployment, folder layout) |
| `docs/decisions/NNNN-title.md` | Architecture Decision Records — one decision each | A choice others must live with (library, data model, protocol) |
| `docs/conventions.md` | Branching, commits, PRs, code style | The team agrees a new rule |
| `AGENTS.md`, `.agents/skills/` | Instructions for agents | A workflow changes (keep them in sync) |

## The feature doc — sections to maintain

Keep the headings from `docs/features/_template.md`:

- **Status** — `Not started` / `In progress` / `In review` / `Done`, plus one line on what works now.
- **Decisions** — dated bullets: what was decided and *why*, e.g.
  `2026-10-30 — Overlap tolerance is 0.5% of the new project's area (client interview, mock-up).`
- **API** — table of endpoints: method, path, roles, purpose. Keep it matching the code.
- **Pages** — route, roles, what it shows.
- **Data model** — tables and important columns.
- **Open questions** — things to ask the team/client; remove when answered (move the answer to Decisions).
- **Progress log** — newest last. One entry per working session or branch:

```markdown
### 2026-10-30 · feature/F2-overlap-engine
- Done: Boundary model + migration; overlap service with tolerance; 9 tests
- Next: POST /api/boundaries/check endpoint; show result on the map page
- Notes: ST_Area needs a geography cast for m² — see service.py
```

## Rules

- Write for a teammate who has never seen your code. Short sentences, concrete names (file paths,
  endpoint paths, table names).
- Record **why**, not just what — the code already says what.
- Update docs in the same commit as the change they describe (`docs(F2): …` alone is fine for
  doc-only updates).
- Don't paste large code blocks — link to the file.
- Never put secrets or real personal data in docs.

## Decision records

Copy the format of `docs/decisions/0001-docker-only-local-development.md`: Context, Decision,
Consequences. Number sequentially. Link it from the feature doc's Decisions list.
