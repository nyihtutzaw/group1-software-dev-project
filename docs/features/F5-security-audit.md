# F5 — Security & auditability

> Context doc for people and AI agents. Read before working on this feature; update before you stop.
> How: `.agents/skills/write-docs/SKILL.md`.

| | |
|---|---|
| **Owner** | Put Thitisawat (security & audit). Deployment (Docker, GitHub Actions CI/CD, Google Cloud) is led by Nyi Htut Zaw, with Put Thitisawat helping |
| **Issue** | [#7](https://github.com/nyihtutzaw/group1-software-dev-project/issues/7) — requirements and acceptance checklist |
| **Requirements** | FR-07 Immutable audit history · FR-09 Audit logging · FR-10 User & role management · WBS 9.0 |
| **Code** | `backend/app/auth/`, `backend/app/features/audit/` · `frontend/src/features/audit/`, `frontend/src/auth/` |
| **Mock-up** | *Ledger* (Audit ledger); role switcher → real sign-in |

## Status

In progress: production JWT secrets are validated, login cookies use `Secure`, and demo seeding is
blocked. The hash-chained ledger behind `record_action()` (#31), the paginated ledger API and the
integrity timeline page are complete. Failed sign-ins and forbidden requests are recorded in a
separate security log, and repeated sign-in failures are temporarily blocked. Admins can list and
create accounts, change roles, and deactivate or reactivate users from `/admin/users`, and each
change is written to the ledger. Security events older than 90 days are deleted automatically.
A **System** menu holds admin settings; its *Role & Access* page shows the role, page-access and
API-access matrices read-only, and *Tutorials* walks through every feature (F1–F5) with annotated
screenshots and a sample project, with the same content as a downloadable PDF user manual.

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
2. The access matrix is enforced; unauthorised access is blocked and logged (9.1.2). ✅ 403 responses are logged; admins can view the matrix at System › Role & Access.
3. The same user cannot both submit and approve a critical action (9.1.3).
4. Ledger records are hash-chained; tampering is detectable (9.2.1).
5. 100% of critical verification and issuance actions are recorded (9.2.2).
6. Admin actions are logged; a retention policy is enforced (9.3.1). ✅ Admin actions are in the ledger; security events are deleted after 90 days; evidence retention in production is #20.
7. Admins can create users, assign roles and deactivate accounts.

## Decisions

- 2026-11-14 — **Hash-chained ledger table design (#31)**:
  `ledger_entries` table with auto-incrementing `id`, `created_at` (UTC), `action` (string),
  `actor_id` (FK `users.id`, nullable for system actions), `actor_email` (snapshot), `entity`,
  `entity_id`, `payload` (JSON), `prev_hash` (hex sha256), and `hash` (hex sha256).
  Formula: `hash = sha256(prev_hash || canonical_json(entry))`. Genesis `prev_hash` is `'0' * 64`.
  An `immutable_ledger_entries` PostgreSQL BEFORE UPDATE OR DELETE trigger blocks modifications
  at the DB level. `record_action()` signature remains unchanged and inserts into caller transaction.
- 2026-11-19 — **Ledger read scope.** The design report says buyers read the ledger, but returning
  all of it exposed every user's email, file names and projects the buyer was never granted
  (WBS 8.1.1, 8.3.1). Now registry staff and admins read every entry; a verifier reads the entries
  of projects currently assigned to them (WBS 7.1.1); a buyer reads entries of granted projects,
  their own allocations and their own access grants, with `actor_id`/`actor_email` removed (the
  role stays) and the payload limited to the fields in `BUYER_PAYLOAD_FIELDS`
  (`backend/app/features/audit/scope.py`). `/api/ledger/verify` still checks the whole chain for
  every allowed role and returns only valid/error.
- 2026-11-15 — **Ledger actor role snapshot (#32)**: preserve the actor's role when each action is
  recorded so the timeline does not misstate a historical role after an account role change.
- 2026-11-15 — **Security events and retention (#34/#35)**: keep failed sign-ins and 403 events in
  a separate security log so attack traffic does not pollute the critical-action ledger. Retain
  ledger entries indefinitely, evidence for 7 years, and security events for 90 days. Apply a
  temporary 15-minute block after 5 failed sign-ins for the same normalized account and source IP
  within 15 minutes. Hash normalized account identifiers with the application secret in the log.
  Retention periods are policy decisions. *(Deletion added 2026-11-19, below.)*
- 2026-11-19 — **Security events are deleted after 90 days** (WBS 9.3.1). Each
  `record_security_event()` first deletes events older than 90 days, so the policy holds without a
  scheduler (the hosted demo scales to zero). `python -m app.features.audit.retention` runs the same
  deletion by hand or from a scheduled job. The ledger is never deleted; evidence retention is the
  production bucket's retention lock (#20).

- 2026-11-19 — **Access matrix is read from the code, not stored**: `require_roles()` tags its
  checker with `allowed_roles`, and `GET /api/admin/access-matrix` walks the mounted routes
  (`fastapi.routing.iter_route_contexts`, as FastAPI's OpenAPI does) to list who may call each
  endpoint. The page matrix comes from `layout/nav.ts`. Nothing can drift or be edited at run time;
  changing access means a code change and a reviewed PR. Ownership rules inside services are not
  shown.
- 2026-11-19 — **System menu**: admin settings pages go under one collapsible *System* parent
  (`NavItem.group = 'system'`, paths `/system/<slug>`). *Users* stays a top-level menu for now.
- 2026-11-19 — **Tutorials are static, frontend-only content**: walkthroughs live in
  `frontend/src/features/tutorials/content.ts` with real screenshots (WebP, 1280 px wide) in
  `images/`, and sample files in `frontend/public/tutorials/samples/`. No API or database, because
  the content only changes when the UI does, through a reviewed PR. Every walkthrough follows one
  fictional project, *Nam Wa Hillside Reforestation* (crediting 2025–2044, 368 ha, vintage 2026,
  4,800 t issued), so the screens connect from registration to a retired credit. A mark's
  `x/y/w/h` are percentages of its screenshot, so marks scale with the image. Issuing credits has
  no button yet, so that step shows the API docs. Admin-only for now, like the rest of System.
  **Refreshing a screenshot:** sign in locally with the demo accounts, take a 1280 px-wide
  screenshot of the same state, save it as WebP, then update the step's `size` and marks.
- 2026-11-19 — **The PDF user manual is a saved file built from the tutorials**: *Download PDF* on
  the Tutorials pages downloads `frontend/public/tutorials/CRVR-User-Manual.pdf` (A4, 36 pages,
  version and date in `MANUAL` in `content.ts`). It is printed from `/system/tutorials/manual`, so
  it always says the same as the walkthroughs. **Regenerate it whenever the tutorials change:**
  open that page and use *Print / Save as PDF* (A4, background graphics on). The committed file
  was printed with headless Chromium using JPEG copies of the screenshots and a page-number
  footer, which keeps it at 3.7 MB. Chrome's own Save as PDF re-encodes WebP losslessly (about
  8 MB) and adds no page numbers.

- 2026-10-28 — **F2 added a `record_action()` stub** in `backend/app/features/audit/ledger.py`
  (`record_action(db, *, actor, action, entity, entity_id, payload)`, logs only). Replace the body
  with the hash-chained insert; keep the signature. F2 already calls it (`boundary.saved`,
  `boundary.overlap_detected`, `boundary.overlap_cleared`, `boundary.overlap_disputed`,
  `boundary.overlap_resolved`).

- 2026-10-27 — Credentials in our own Postgres (bcrypt hashes), not Keycloak/Auth0, for now —
  see [ADR 0002](../decisions/0002-database-backed-authentication.md).
- 2026-10-27 — Session = JWT (HS256, 8 h) in an httpOnly, SameSite=Lax cookie named
  `crvr_session`; `Secure` in production. The frontend never sees the token.
- 2026-11-15 — **Production authentication settings (#38)**: production requires a non-default
  `JWT_SECRET` with at least 32 bytes. Cloud Run supplies it from Secret Manager as an environment
  variable; the app does not fetch secrets directly. Production blocks demo-data seeding.
- 2026-10-27 — Roles: `developer`, `verifier`, `registry_staff`, `buyer`, `admin` (Charter FR-10).
- 2026-10-27 — Ledger lives in a PostgreSQL table (append-only), not a separate service.
- 2026-11-15 — User creation requires an admin-provided initial password of at least 12 characters
  and at most 72 UTF-8 bytes (bcrypt's input limit). Only the password hash is stored; the password
  is never returned or included in audit payloads. Admins cannot change their own role or deactivate
  themselves; active admin rows are locked while changing an admin account to prevent concurrent
  changes from removing all active admins.

### Cloud Run production configuration

- Set `APP_ENV=production`; the login endpoint then sets the cookie's `Secure` flag.
- Generate a cryptographically random `JWT_SECRET` with `openssl rand -base64 32` and store it in
  Google Secret Manager. Configure Cloud Run to expose that secret as `JWT_SECRET`, and grant the
  service account Secret Manager Secret Accessor on that secret.
- Set `SEED_DEMO_USERS=false`. The seed functions also reject calls when `APP_ENV=production`.

## API

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/api/auth/login` | public | Sign in; sets cookie, records failures, and rate-limits repeated failures |
| POST | `/api/auth/logout` | any | Clear the session cookie |
| GET | `/api/auth/me` | signed-in | Current user |
| GET | `/api/auth/demo-accounts` | public (dev only) | Demo accounts for one-click sign-in; empty on the hosted demo |
| GET | `/api/admin/users` | admin | List users without credential data |
| POST | `/api/admin/users` | admin | Create a user with an admin-provided initial password |
| PATCH | `/api/admin/users/{user_id}` | admin | Change a user's role or active status |
| GET | `/api/admin/access-matrix` | admin | Every API endpoint with the roles allowed to call it (read-only) |
| GET | `/api/ledger` | verifier, registry_staff, buyer, admin | Paginated ledger entries, newest first. Staff/admin: all. Verifier: assigned projects. Buyer: granted projects, no actor email/ID, traceability payload fields only |
| GET | `/api/ledger/verify` | verifier, registry_staff, buyer, admin | Verify cryptographic integrity of ledger chain |

## Pages

| Route | Roles | Shows |
|---|---|---|
| `/login` | public | Sign-in + demo accounts (dev) |
| `/ledger` | verifier, registry_staff, buyer, admin | Paginated audit timeline with chain integrity status |
| `/admin/users` | admin | List accounts, create users, change roles, and deactivate or reactivate accounts |
| `/system/roles-access` | admin | System › Role & Access: roles, page-access and API-access matrices, read-only |
| `/system/tutorials` | admin | System › Tutorials: one walkthrough card per feature (F1–F5) |
| `/system/tutorials/manual` | admin | Printable user manual (cover, how to read, roles, contents, one page per step), without the app shell. Source of `public/tutorials/CRVR-User-Manual.pdf` |
| `/system/tutorials/:id?step=N` | admin | One walkthrough: annotated screenshot per step, numbered legend, who does the step, link to the real page, sample data and files |

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
- User invitation, password-change and password-reset flows are not included; users receive their
  initial password out of band.

## Progress log

### 2026-11-19 · feature/F5-admin-tutorials
- Goal: a *Tutorials* page under System (admin) that walks through each feature (F1–F5) step by
  step, using real screenshots with numbered marks, a sample project and downloadable sample files.
- Plan: 1) sample files and screenshots of a fictional project taken through the whole flow
  2) tutorial content, annotated-screenshot component, list and walkthrough pages + route/menu
  3) tests 4) docs.
- Done: 28 screenshots taken with Playwright while the sample project went through registration,
  boundary, assignment, sign-off, approval, issuance, buyer access, allocation and retirement.
  Five walkthroughs (6 + 4 + 8 + 6 + 4 steps). The legend and marks highlight each other on
  hover/focus; on phones the legend follows the screenshot. Pages are lazy-loaded (main bundle
  434 → 341 kB). New shared `book` icon.
- Validation: frontend format, lint, typecheck, 102 tests and production build pass; checked in
  light and dark themes and at 420 px.
- Then: light theme is the default for everyone (ADR 0004 updated). Added the printable manual
  page, the generated PDF and a *Download PDF* button on the tutorials list and every
  walkthrough. Validation: 108 frontend tests, lint, typecheck, format and build pass; the PDF was
  rendered page by page and checked; the button downloads `CRVR-User-Manual.pdf`.
- Note: making the screenshots added two projects to the local dev DB: CRVR-0203 (a first try,
  verified but not issued because its crediting period started in the future) and CRVR-0204 (the
  sample). `sh scripts/start.sh --fresh --yes` clears them.

### 2026-11-19 · fix/hide-hosted-demo-accounts
- Fix: the hosted demo's public sign-in page listed every demo account (including admin), which
  advertises the accounts to anyone who finds the URL. `/api/auth/demo-accounts` now returns the
  list only when the demo password is the public development one, so only local development shows
  it (one-click sign-in unchanged). Account e-mails go to the professor with the private password
  (`docs/deployment.md`). Tests updated in `test_deployment.py` and `LoginPage.test.tsx`.

### 2026-11-19 · feature/F5-role-access-matrix
- Goal: a **System** menu group for admins, with a first child page **Role & Access** that shows the
  role and access matrix as read-only tables (acceptance criterion 2: the access matrix).
- Plan: 1) admin-only `GET /api/admin/access-matrix`, read from each route's `require_roles`
  2) menu groups in `layout/nav.ts` (sidebar section, one tab on phones, breadcrumb)
  3) `/system/roles-access` page with roles, page-access and API-access tables 4) tests + this doc
- Done: `require_roles()` tags its checker with `allowed_roles`; the admin-only
  `GET /api/admin/access-matrix` lists every `/api` endpoint with its area, summary and allowed
  roles (or public / any signed-in user). `nav.ts` supports parent menus (`group`, `menuEntries`,
  `isUnder`); the sidebar shows *System* as a collapsible section, phones get one *System* tab and
  the breadcrumb shows *System › Role & Access*. The page has three tables (roles, page access,
  API access) and no editing controls. New `settings` and `shield` icons in the UI kit.
- Note: FastAPI 0.162 mounts included routers lazily, so `app.routes` is not flat; the matrix uses
  `iter_route_contexts` to get the effective routes.
- Validation: backend Ruff and all 252 tests passed; frontend Prettier, ESLint, typecheck, all 90
  tests and the production build passed.
- Next: move other admin settings (e.g. *Users*) under *System* if the team agrees.

### 2026-11-19 · fix/F5-security-event-retention
- Done: `backend/app/features/audit/retention.py` deletes security events older than 90 days;
  called on every new security event and runnable as a command. Tests in
  `tests/test_security_retention.py` (boundary at exactly 90 days, deletion on record, ledger
  untouched).

### 2026-11-19 · fix/F5-ledger-scope
- Fix: buyers could read the whole ledger (all user emails, evidence file names, other projects'
  entries) and verifiers every project's entries. `/api/ledger` is now scoped per role (see the
  2026-11-19 decision). The ledger page shows the role alone when the email is hidden.
- Tests: `tests/test_ledger_scope.py` (staff all, verifier assigned only, buyer granted only and
  redacted, no-grant buyer sees nothing); `test_audit.py` updated; frontend actor label tests.

### 2026-11-15 · fix/admin-user-local-email
- Fix: creating a user at `/admin/users` rejected `@crvr.local` emails (the domain of the demo and
  team accounts), because `EmailStr` refuses reserved domains such as `.local`. The admin form now
  checks only the address shape (`name@domain.tld`). Tests added for both cases.

### 2026-11-15 · feature/F5-user-management
- Goal: complete #33 with admin-only user listing, creation, role changes and deactivation.
- Decision: an admin supplies the new account's initial password because no invite or reset flow
  exists; the API stores only its password hash and never returns the password.
- Plan: add typed admin-user schemas and service/router with role enforcement and `record_action()`
  calls; cover validation, RBAC, self/last-admin safeguards and audit calls; implement the Users
  page and focused frontend tests; update this doc and run the relevant Docker checks.
- Dependency: persisted admin-action audit entries require the hash-chain implementation in #31.
- Done: `/api/admin/users` supports admin-only list/create/patch; creation normalizes and validates
  email, rejects duplicates, hashes the initial password, and returns no credential data. Role
  changes, activation and deactivation emit audit calls; self-access changes are blocked. The
  responsive page lists accounts and provides create, role-change and confirm-before-deactivate
  controls. No migration was needed.
- Validation: 13 backend auth/admin-user tests and 5 Users page tests passed; backend Ruff,
  frontend ESLint, TypeScript, Prettier and production build passed. Tests used a new isolated
  database because the existing local database is stamped at #31's unmerged ledger migration;
  that database was left untouched.
- Next: after #31 lands, verify admin actions are persisted by the ledger, then complete review and
  merge #33.

### 2026-11-15 · feature/F5-security-controls
- Goal: complete #34 and #35: record failed sign-ins and 403s, enforce temporary login lockout, and document retention periods.
- Done: added the `security_events` table and migration, hashed sign-in subjects, recorded failed and successful sign-ins plus 403 responses, and enforced a persistent 5-failure/15-minute lockout per normalized account and source IP.
- Validation: targeted auth/audit tests passed (19); full backend suite passed (183); Ruff checks and formatting passed; Alembic has one head and `alembic check` reports no new upgrade operations.
- Decisions: separate security-event log; retain security events 90 days, evidence 7 years, and the append-only ledger indefinitely. Automated retention cleanup is not implemented.
- Dependency: #31/#32 are unmerged and this branch is stacked on their branch; #33 already emits ledger actions on its separate branch.
- Next: integrate #33 admin-action logging, decide/implement scheduled retention cleanup if required, then rebase and open the combined PR after #31/#32 merge.

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

### 2026-11-15 · feature/F5-production-settings
- Goal: complete #38 by making production authentication settings fail safely before Cloud Run deployment.
- Plan: validate the production JWT secret at settings load, guard demo-data seed functions, test production cookie/secret/seeding behavior, and document Cloud Run Secret Manager configuration.
- Done: reject the development or shorter-than-32-byte JWT secret in production; keep the login cookie secure in production; prevent both demo seed functions from running in production; document Secret Manager injection and Cloud Run settings.
- Validation: focused config, seed, and auth tests passed (14); full backend pytest passed; Ruff
  checks passed and all 67 backend files are formatted. One existing Starlette/httpx deprecation
  warning remains.
