---
name: sync-branch
description: Bring the latest main into a CRVR feature branch by rebasing, resolve merge conflicts (including Alembic migration conflicts and lock files), and push safely. Use when main has moved on, before opening a PR, or when a PR shows conflicts.
---

# Sync a branch with main

We **rebase** feature branches on `main` (history stays linear; PRs are squash-merged anyway).

## 1. Start clean

```bash
git status --short     # commit or stash first
git fetch origin
git log --oneline HEAD..origin/main   # what is new on main
```

## 2. Rebase

```bash
git rebase origin/main
```

If it stops with conflicts:

```bash
git status                          # lists conflicted files
# edit each file: keep both sides' intent, remove the <<<<<<< ======= >>>>>>> markers
git add <file>
git rebase --continue
```

`git rebase --abort` returns to where you started if it gets confusing — then ask the user.

### Typical conflicts

| File | What to do |
|---|---|
| `backend/app/main.py` | Usually two routers added — keep both `include_router` lines |
| `frontend/src/App.tsx`, `layout/nav.ts` | Keep both routes / nav items |
| `uv.lock` / `package-lock.json` | Do not hand-merge. Take main's version with `git checkout origin/main -- <file>`, regenerate it (`docker compose exec backend uv lock` or `docker compose exec frontend npm install`), then `git add` it |
| Feature docs | Keep both entries, newest progress-log entry last |

### Alembic: two migration heads

If both main and your branch added a migration, there are two heads after the rebase:

```bash
docker compose exec backend alembic heads           # shows 2 revisions → conflict
```

Fix by re-pointing **your** migration at main's latest one: open your migration file and set
`down_revision` to the other head's revision id (and update `Revises:` in the docstring). Then:

```bash
docker compose exec backend alembic heads           # exactly 1 head now
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
```

## 3. Re-run the checks

Run the full checks (`dev-environment` → *Checks*). If dependencies changed on main:
`docker compose up -d --build -V`.

## 4. Push

A rebase rewrites your branch, so a plain push is rejected. Use the safe force:

```bash
git push --force-with-lease
```

Never force-push `main`, and never force-push a branch someone else is also committing to without
asking them.
