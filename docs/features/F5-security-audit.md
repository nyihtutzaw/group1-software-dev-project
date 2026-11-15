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

In progress (`feature/F5-security-controls`, stacked on the unmerged #31/#32 branch): failed
sign-ins and forbidden requests are being recorded in a separate security log, with rate limiting
and agreed retention periods. #33 admin actions remain on their separate user-management branch.

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

- 2026-11-14 — **Hash-chained ledger table design (#31)**:
  `ledger_entries` table with auto-incrementing `id`, `created_at` (UTC), `action` (string),
  `actor_id` (FK `users.id`, nullable for system actions), `actor_email` (snapshot), `entity`,
  `entity_id`, `payload` (JSON), `prev_hash` (hex sha256), and `hash` (hex sha256).
  Formula: `hash = sha256(prev_hash || canonical_json(entry))`. Genesis `prev_hash` is `'0' * 64`.
  An `immutable_ledger_entries` PostgreSQL BEFORE UPDATE OR DELETE trigger blocks modifications
  at the DB level. `record_action()` signature remains unchanged and inserts into caller transaction.
- 2026-11-15 — **Ledger actor role snapshot (#32)**: preserve the actor's role when each action is
  recorded so the timeline does not misstate a historical role after an account role change.
- 2026-11-15 — **Security events and retention (#34/#35)**: keep failed sign-ins and 403 events in
  a separate security log so attack traffic does not pollute the critical-action ledger. Retain
  ledger entries indefinitely, evidence for 7 years, and security events for 90 days. Apply a
  temporary 15-minute block after 5 failed sign-ins for the same normalized account and source IP
  within 15 minutes. Hash normalized account identifiers with the application secret in the log.

- 2026-10-28 — **F2 added a `record_action()` stub** in `backend/app/features/audit/ledger.py`
  (`record_action(db, *, actor, action, entity, entity_id, payload)`, logs only). Replace the body
  with the hash-chained insert; keep the signature. F2 already calls it (`boundary.saved`,
  `boundary.overlap_detected`, `boundary.overlap_cleared`, `boundary.overlap_disputed`,
  `boundary.overlap_resolved`).

- 2026-10-27 — Credentials in our own Postgres (bcrypt hashes), not Keycloak/Auth0, for now —
  see [ADR 0002](../decisions/0002-database-backed-authentication.md).
- 2026-10-27 — Session = JWT (HS256, 8 h) in an httpOnly, SameSite=Lax cookie named
  `crvr_session`; `Secure` in production. The frontend never sees the token.
- 2026-10-27 — Roles: `developer`, `verifier`, `registry_staff`, `buyer`, `admin` (Charter FR-10).
- 2026-10-27 — Ledger lives in a PostgreSQL table (append-only), not a separate service.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/api/auth/login` | public | Sign in; sets cookie, records failures, and rate-limits repeated failures |
| POST | `/api/auth/logout` | any | Clear the session cookie |
| GET | `/api/auth/me` | signed-in | Current user |
| GET | `/api/auth/demo-accounts` | public (dev only) | Demo accounts for the sign-in page |
| GET | `/api/ledger` | verifier, registry_staff, buyer, admin | Paginated ledger entries, newest first |
| GET | `/api/ledger/verify` | verifier, registry_staff, buyer, admin | Verify cryptographic integrity of ledger chain |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/login` | public | Sign-in + demo accounts (dev) |
| `/ledger` | verifier, registry_staff, buyer, admin | Paginated audit timeline with chain integrity status |
| `/admin/users` | admin | User management — placeholder |

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `users` | email (unique), full_name, organization, role, password_hash, is_active | migration 0001 |
| `ledger_entries` | id, created_at, action, actor_id, actor_email, actor_role, entity, entity_id, payload, prev_hash, hash | migrations e24ad4024afd and f13d8a1b0c2e (append-only trigger blocks UPDATE/DELETE) |
| `security_events` | id, created_at, event_type, actor_id, subject_hash, source_ip, method, path, status_code | Stores access denials and sign-in events; 90-day retention policy |

## Depends on / used by

- Used by every feature: `require_roles()`, and `record_action(...)` for the ledger — agree its
  signature early so F1–F4 can call it.

## Open questions

- Automatic evidence expiry requires production object-storage lifecycle support; the current local
  filesystem does not enforce the agreed 7-year retention period.

## Progress log

### 2026-11-15 · feature/F5-security-controls
- Goal: complete #34 and #35: record failed sign-ins and 403s, enforce temporary login lockout, and document retention periods.
- Decisions: separate security-event log; 5 failed attempts per normalized account + IP in 15 minutes trigger a 15-minute block; retain security events 90 days, evidence 7 years, and the append-only ledger indefinitely.
- Plan: add security-event model/migration and logging helpers; log login failures and all 403 responses; enforce persistent rate limiting; add focused tests and document behavior.
- Dependency: #31/#32 are unmerged and this branch is stacked on their branch; #33 already emits ledger actions on its separate branch.

### 2026-11-15 · feature/F5-ledger-page
- Goal: complete #32 on top of the #31 ledger implementation.
- Plan: add a paginated ledger endpoint; implement the responsive timeline, status alert, and role-aware integrity check; test API and UI behavior; validate and update this doc.
- Dependency: #31 is not yet merged; this branch is based on its open implementation branch.
- Decision: expose the read-only chain integrity result to buyers as well as other ledger readers; the mock-up shows the chain status on the shared ledger page.
- Done: `/api/ledger` returns newest-first pages; the timeline shows action, actor and role snapshot, time, short hash and payload details. Buyers can see the read-only integrity status. Added an additive migration for historical actor-role snapshots.
- Validation: backend Ruff checks, migration consistency, and all 180 backend tests passed; frontend formatting, lint, typecheck, all 60 frontend tests, and production build passed.
- Next: after #31 merges, rebase on `main`, rerun checks, then open the #32 PR.

### 2026-11-14 · feature/F5-ledger-table
- Goal: store critical actions in an append-only, hash-chained ledger table behind `record_action()` (#31)
- Done:
  - `ledger_entries` model and Alembic migration `e24ad4024afd`.
  - Database-level trigger `ledger_entries_no_update_delete` raising `insufficient_privilege` on UPDATE or DELETE.
  - Implemented `record_action()` in `backend/app/features/audit/ledger.py` with transaction advisory lock and deterministic canonical JSON hash calculation `sha256(prev_hash || canonical_json(entry))`.
  - Added `verify_ledger_chain(db)` utility to detect tampering, gap deletion, or link breakage.
  - Added `GET /api/ledger` and `GET /api/ledger/verify` with role checks.
  - Tests: 9 backend tests in `backend/tests/test_audit.py` covering hash chaining, canonical JSON determinism, tampering detection, deletion gap detection, DB trigger enforcement, rollback on caller error, and RBAC; all 24 boundary tests pass with live ledger writes.
- Next: frontend LedgerPage UI from mock-up, admin user management endpoints & UI, separation-of-duties helper.

### 2026-10-27 · main (initial setup)
- Done: users table, login/logout/me, require_roles, demo seed, frontend sign-in, Guarded routes,
  role-based nav; tests for auth and role checks.
- Next: ledger table + `record_action()`, separation-of-duties helper, user management.
