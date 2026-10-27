Part of #<!-- feature issue: F1 #3 · F2 #4 · F3 #5 · F4 #6 · F5 #7 (use "Closes" only when the feature is complete) -->

## What

<!-- One or two sentences. PR title = Conventional Commit, e.g. feat(F2): overlap detection -->

## Why

<!-- Link the acceptance criteria in docs/features/F<n>-*.md -->

## How to test

1. `docker compose up -d --build`
2.

## Checklist

- [ ] Tests added/updated and passing
- [ ] Feature doc updated (status, decisions, API/pages, progress log)
- [ ] Touches shared code (`core/`, `auth/`, `components/ui/`, `layout/`) — explained above
- [ ] New dependency — team must run `docker compose up -d --build -V`
- [ ] Database migration included
- [ ] UI matches the mock-up (screenshot attached)
