# Team conventions

Short version of how we work. The detailed, step-by-step versions are the agent skills in
`.agents/skills/` — humans can follow them too.

## Branches

- `main` is protected: no direct pushes; changes arrive by pull request with 1 approval and green CI.
- One branch per piece of work, cut from the latest `main`:
  `feature/F<n>-<slug>` · `fix/<slug>` · `docs/<slug>` · `chore/<slug>`
- Keep branches short-lived (1–3 days). A feature is usually several branches in a row.
- Update with `git rebase origin/main`, push with `git push --force-with-lease`.

## Commits

- Commit after every working step; push at least at the end of each session.
- Conventional Commits: `<type>(<scope>): <imperative summary>`
  - types: `feat` `fix` `test` `refactor` `docs` `style` `chore` `ci` `perf`
  - scopes: `F1`…`F5`, `backend`, `frontend`, `auth`, `ui`, `db`, `infra`, `docs`, `agents`
- Model changes and their migration go in the same commit.
- No AI attribution in commits or PRs (no `Co-Authored-By:` trailers or "Generated with …" lines).

## Pull requests

- Title in Conventional Commits form — PRs are **squash-merged**, so the title becomes the commit on
  `main`.
- Fill in the template: what, why, how to test, checklist.
- Mention any change to shared code (`core/`, `auth/`, `components/ui/`, `layout/`) and any new
  dependency or migration.
- The branch is deleted automatically after merge.

## Code

- Backend: ruff (format + lint), type hints everywhere, business logic in `service.py`, every
  non-public route uses `require_roles`. Tests for every acceptance criterion and role rule.
- Frontend: ESLint + Prettier, TypeScript strict, UI kit + design tokens only (no hex colours),
  phone-first layouts. Tests with Testing Library.
- Each feature stays in its own folders; shared code changes are called out.

## Docs

- Each feature keeps `docs/features/F<n>-*.md` current — status, decisions, API, pages, progress log.
- Decisions others must live with get an ADR in `docs/decisions/`.
