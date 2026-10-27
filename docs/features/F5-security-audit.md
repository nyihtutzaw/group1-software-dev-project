# F5 — Security & auditability

> Context doc for people and AI agents. Read before working on this feature; update before you stop.
> How: `.agents/skills/write-docs/SKILL.md`.

| | |
|---|---|
| **Owner** | Put Thitisawat (also: Docker, GitHub Actions, Cloud Run; supported by Nyi Htut Zaw) |
| **Issue** | [#7](https://github.com/nyihtutzaw/group1-software-dev-project/issues/7) — requirements and acceptance checklist |
| **Requirements** | FR-07 Immutable audit history · FR-09 Audit logging · FR-10 User & role management · WBS 9.0 |
| **Code** | `backend/app/auth/`, `backend/app/features/audit/` · `frontend/src/features/audit/`, `frontend/src/auth/` |
| **Mock-up** | *Ledger* (Audit ledger); role switcher → real sign-in |

## Status

Partly in place (app shell): email + password sign-in, httpOnly JWT cookie, five roles,
`require_roles()` on the API and role-based menus/route guards on the frontend, seeded demo users.
Ledger, user management and separation-of-duties enforcement not started.

## Scope

Authentication and role-based access control across the five charter roles, with separation of
duties enforced in software. Every critical action — submission, boundary change, verification
decision, approval, issuance — is written to an **append-only ledger** in which each entry carries a
cryptographic hash of the one before it, so any later alteration breaks the chain and becomes
visible. Evidence files are held in write-once storage.

**Out of scope:** blockchain / distributed ledger (rejected in the design), the inter-registry
flagging hook (deferred).

## Acceptance criteria

From WBS 9.x and the design report:

1. All users authenticate; sessions are managed securely (9.1.1). ✅ shell
2. The access matrix is enforced; unauthorised access is blocked and logged (9.1.2). Partly ✅ (blocked, not yet logged)
3. The same user cannot both submit and approve a critical action (9.1.3).
4. Ledger records are hash-chained; tampering is detectable (9.2.1).
5. 100% of critical verification and issuance actions are recorded (9.2.2).
6. Admin actions are logged; a retention policy is enforced (9.3.1).
7. Admins can create users, assign roles and deactivate accounts.

## Decisions

- 2026-10-28 — **F2 added a `record_action()` stub** in `backend/app/features/audit/ledger.py`
  (`record_action(db, *, actor, action, entity, entity_id, payload)`, logs only). Replace the body
  with the hash-chained insert; keep the signature. F2 already calls it (`boundary.saved`,
  `boundary.overlap_detected`, `boundary.overlap_disputed`, `boundary.overlap_resolved`).

- 2026-10-27 — Credentials in our own Postgres (bcrypt hashes), not Keycloak/Auth0, for now —
  see [ADR 0002](../decisions/0002-database-backed-authentication.md).
- 2026-10-27 — Session = JWT (HS256, 8 h) in an httpOnly, SameSite=Lax cookie named
  `crvr_session`; `Secure` in production. The frontend never sees the token.
- 2026-10-27 — Roles: `developer`, `verifier`, `registry_staff`, `buyer`, `admin` (Charter FR-10).
- 2026-10-27 — Ledger lives in a PostgreSQL table (append-only), not a separate service.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/api/auth/login` | public | Sign in; sets the session cookie |
| POST | `/api/auth/logout` | any | Clear the session cookie |
| GET | `/api/auth/me` | signed-in | Current user |
| GET | `/api/auth/demo-accounts` | public (dev only) | Demo accounts for the sign-in page |
| GET | `/api/ledger` | verifier, registry_staff, buyer, admin | Ledger entries (placeholder) |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/login` | public | Sign-in + demo accounts (dev) |
| `/ledger` | verifier, registry_staff, buyer, admin | Audit ledger — placeholder |
| `/admin/users` | admin | User management — placeholder |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `users` | email (unique), full_name, organization, role, password_hash, is_active | migration 0001 |
| — | | `ledger_entries` (seq, action, actor_id, payload, prev_hash, hash) to be designed |

## Depends on / used by

- Used by every feature: `require_roles()`, and `record_action(...)` for the ledger — agree its
  signature early so F1–F4 can call it.

## Open questions

- Login rate limiting / lockout?
- Should failed sign-ins and 403s go into the ledger or a separate security log?

## Progress log

### 2026-10-27 · main (initial setup)
- Done: users table, login/logout/me, require_roles, demo seed, frontend sign-in, Guarded routes,
  role-based nav; tests for auth and role checks.
- Next: ledger table + `record_action()`, separation-of-duties helper, user management.
