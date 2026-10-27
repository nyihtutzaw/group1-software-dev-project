---
name: commit
description: Commit work on a CRVR branch the team's way — run the checks, stage only the intended files, and write a Conventional Commits message with the feature scope. Use after every working step, and whenever the user asks to commit or save progress.
---

# Commit

Commit **often**: one commit per working step (a model + its migration, a service + its tests, a
page). A reviewer should be able to read the branch commit by commit.

## 1. Never on main

```bash
git branch --show-current     # if this prints "main", stop: create a branch (start-feature)
```

## 2. Run the checks for what you changed

See `dev-environment` → *Checks*. Do not commit failing tests or lint errors. If a check fails for
a reason outside your change, say so in the commit body.

## 3. Stage deliberately

```bash
git status --short
git add backend/app/features/boundary/ backend/migrations/versions/20261028_ab12_add_boundaries.py
git diff --cached --stat      # review exactly what is going in
```

- Stage files by path. Avoid `git add -A` / `git add .` unless you have checked `git status`.
- Never stage `.env`, credentials, `node_modules`, build output, or large data files.
- A model change and its migration go in the **same** commit.
- If the step changed the feature doc (decision, endpoint, progress), include it.

## 4. Message format — Conventional Commits

```
<type>(<scope>): <summary in imperative mood, ≤ 72 chars, no full stop>

<optional body: why, not what — wrap at 72>
```

- **type**: `feat` new behaviour · `fix` bug · `test` tests only · `refactor` no behaviour change ·
  `docs` · `style` formatting · `chore` tooling/deps · `ci` · `perf`
- **scope**: `F1`…`F5` for feature work; otherwise `backend`, `frontend`, `auth`, `ui`, `db`,
  `infra`, `docs`, `agents`
- Mention shared-code changes in the body ("Also touches components/ui/Alert: adds `info` tone").

Examples:

```
feat(F2): store project boundaries as PostGIS polygons
test(F2): cover overlap tolerance at 0.5% boundary
fix(F3): show overdue flag on the due date itself
docs(F4): record traceability endpoint decision
chore(backend): add shapely for geometry validation
```

Use a heredoc for multi-line messages:

```bash
git commit -F- <<'MSG'
feat(F2): block submission when overlap exceeds tolerance

Overlap above 0.5% of the project area marks the boundary as
conflicting; the registration step refuses to continue until it is
resolved or disputed.
MSG
```

Add your tool's co-author trailer if it has one (e.g. `Co-Authored-By: …`).

## 5. Push

Push after each commit or at least at the end of every session, so work is never only on one
laptop: `git push` (first time on a branch: `git push -u origin HEAD`).
