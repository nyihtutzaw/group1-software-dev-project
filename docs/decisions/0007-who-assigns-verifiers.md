# 0007 — Registry staff and admin assign verifiers

**Date:** 2026-11-19 · **Status:** Accepted (issue #28)

## Context

F3 left open who may assign a project to a verifier: registry staff only, admin only, or both.
The assign endpoint already allowed both, because both roles can open the verification queue and
admin can perform every other registry action (resolving an overlap, issuing credits).

## Decision

- **Registry staff and admin** may assign a verifier and a due date, and may reassign either after
  a rejection or a request for changes.
- A **verifier cannot assign or reassign**, including their own work. The API enforces this with
  `require_roles(Role.REGISTRY_STAFF, Role.ADMIN)` on both endpoints.
- Admin is the operational fallback when staff are unavailable, not a second maker in the
  maker-checker step. Approving a sign-off is still blocked for the person who signed off and for
  the project owner.

## Consequences

- No change to who can call `POST /api/verifications/assignments`.
- `PATCH /api/verifications/assignments/{id}` uses the same roles.
- The open question in `docs/features/F3-verification.md` is closed.
