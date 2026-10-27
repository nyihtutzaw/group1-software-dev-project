---
name: start-feature
description: Start work on a CRVR feature (F1–F5) or a new slice of one — update main, create the correctly named branch, read or create the feature context doc, and make the first commit. Use whenever the user says "start", "begin", "work on F2", or asks for something that is not on a branch yet.
---

# Start a feature

One branch per piece of work. A feature (e.g. F2) can have several branches over time
(`feature/F2-boundary-model`, then `feature/F2-overlap-engine`) — keep each one small enough to
review in one sitting (roughly 1–3 days of work).

## 1. Check where you are

```bash
git status --short          # must be clean — if not, commit or stash first (ask the user)
git branch --show-current
```

If you are already on the right feature branch, skip to step 4.

## 2. Update main and branch from it

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/F2-overlap-engine
```

Branch names: `<type>/<scope>-<slug>`, lowercase, hyphens, ≤ 5 words.

| Type | For | Example |
|---|---|---|
| `feature/F<n>-…` | new behaviour in a feature | `feature/F1-evidence-upload` |
| `fix/…` | a bug | `fix/F3-overdue-date` or `fix/login-redirect` |
| `docs/…` | documentation only | `docs/architecture-diagram` |
| `chore/…` | tooling, CI, dependencies | `chore/ci-cache` |

## 3. Read the context

Read, in order — they are short:

1. The feature's GitHub issue (number in the `AGENTS.md` feature table) — the full requirements,
   user stories and acceptance checklist: `gh issue view <number>` (or open it on GitHub)
2. `docs/features/F<n>-*.md` — status, decisions so far, progress log
3. `docs/architecture.md` — how the pieces fit
4. The mock-up section for this feature in `docs/project/CRVR-Mock-UI-v0.1.html`
5. The existing code in `backend/app/features/<name>/` and `frontend/src/features/<name>/`

Pick the next unticked acceptance criteria from the issue as this branch's goal.

## 4. Plan in the doc, then commit it

Add an entry to the **Progress log** of the feature doc for this branch (see `write-docs`):

```markdown
### 2026-10-28 · feature/F2-overlap-engine
- Goal: detect overlaps between a new boundary and all registered ones, with a 0.5% tolerance
- Plan: 1) boundary model + migration 2) overlap service + tests 3) API endpoint 4) map alert UI
```

Set **Status** to `In progress`. Then commit and publish the branch:

```bash
git add docs/features/F2-boundary.md
git commit -m "docs(F2): plan overlap engine"
git push -u origin HEAD
```

## 5. Build in small steps

Work through the plan one step at a time. After each step works and its checks pass, commit
(`commit` skill). When the plan is done, open a PR (`open-pr` skill).
