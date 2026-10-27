# 0002 — Database-backed authentication (Keycloak/Auth0 later)

**Date:** 2026-10-27 · **Status:** Accepted

## Context

The design report names Keycloak/Auth0 as the identity service. Running Keycloak locally adds a
heavy container (~0.7–1 GB RAM) and setup for every team member, and the course build needs working
roles from day one.

## Decision

Store users in our own `users` table: bcrypt password hashes, one of five roles, an active flag.
Sign-in issues a short-lived HS256 JWT in an httpOnly, SameSite=Lax cookie. Authorisation is done
by the `require_roles()` FastAPI dependency. Demo users (one per role) are seeded in development.

## Consequences

- No extra container; works offline.
- We own password storage, so it must be done carefully: bcrypt, no plain-text logging, generic
  "wrong email or password" errors, `Secure` cookies in production. Rate limiting is an open item
  for F5.
- Swapping to Keycloak/Auth0 later only changes how `get_current_user` resolves the user (OIDC
  token instead of our JWT); `require_roles` and every route stay the same.
