---
name: open-pr
description: Finish a CRVR branch and open a pull request to main — final checks, sync with main, update the feature doc, push, and create the PR with the team template using the gh CLI (or give the compare URL). Use when a branch's plan is done or the user asks for a PR or review.
---

# Open a pull request

## 1. Ready?

- [ ] Every step of the branch plan is done (feature doc → Progress log)
- [ ] All checks pass (`dev-environment` → *Checks*)
- [ ] Branch is up to date with main (`sync-branch`)
- [ ] Feature doc updated: status, decisions, endpoints/pages, what is left (`write-docs`)
- [ ] Nothing unrelated in the diff: `git diff --stat origin/main...HEAD`

## 2. Push

```bash
git push -u origin HEAD      # after a rebase: git push --force-with-lease
```

## 3. Create the PR

Title = the change in Conventional Commits form, because PRs are **squash-merged** and the title
becomes the commit on main: `feat(F2): overlap detection with tolerance gate`.

With the GitHub CLI:

```bash
gh pr create --base main --title "feat(F2): overlap detection with tolerance gate" --body-file - <<'MD'
Part of #4

## What
Detects overlaps between a submitted boundary and every registered boundary; blocks submission
above 0.5% of the project area.

## Why
F2 acceptance criteria 1–3 (docs/features/F2-boundary.md).

## How to test
1. `docker compose up -d --build`
2. Sign in as developer@crvr.local → Map → draw a polygon over CRVR-0092
3. The overlap alert shows the area and percentage; Continue is disabled

## Checklist
- [x] Tests added/updated and passing
- [x] Feature doc updated
- [ ] Touches shared code — none
- [ ] New dependency — none (otherwise: everyone run `docker compose up -d --build -V`)
- [ ] Migration — yes: adds `boundaries` table
MD
```

The body follows `.github/pull_request_template.md`. Add screenshots for UI changes when you can.
**Link the feature issue** (number in the `AGENTS.md` feature table) at the top of the body:
`Part of #4` for a partial step; `Closes #4` only in the PR that completes the whole feature.
**No AI attribution** in the title or body — no "Generated with …" footer, no co-author lines.

Without `gh`: print the compare URL for the user —
`https://github.com/nyihtutzaw/group1-software-dev-project/compare/main...<branch>?expand=1`.

## 4. After opening

- CI runs automatically; fix anything red with new commits on the same branch.
- Ask one teammate to review (at least one approval is needed to merge).
- After the squash-merge, tick the acceptance criteria this PR completed in the feature issue
  (`gh issue view <number>` / edit on GitHub), and clean up locally:

```bash
git switch main && git pull --ff-only
git branch -d feature/F2-overlap-engine
```
