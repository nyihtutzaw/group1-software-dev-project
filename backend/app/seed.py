"""Load demo data: accounts (one per role), projects and boundaries.

Runs in development, and in the hosted class demo (APP_ENV=production with DEMO_MODE=true, where
the accounts get the private DEMO_PASSWORD). Run with `python -m app.seed`. Safe to run
repeatedly: existing records are left alone.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password

# Names follow the UI mock-up (docs/project/CRVR-Mock-UI-v0.1.html).
DEMO_USERS = [
    {
        "email": "developer@crvr.local",
        "full_name": "Somchai Prasert",
        "organization": "Nan Reforestation Co.",
        "role": Role.DEVELOPER,
    },
    {
        # Owns the neighbouring projects on the demo map (F2)
        "email": "developer2@crvr.local",
        "full_name": "Anan Chaiyasit",
        "organization": "Phrae Agroforestry Co.",
        "role": Role.DEVELOPER,
    },
    {
        "email": "verifier@crvr.local",
        "full_name": "Dr. Anna Weber",
        "organization": "TUV Nord (VVB-114)",
        "role": Role.VERIFIER,
    },
    {
        "email": "staff@crvr.local",
        "full_name": "Naree Suwan",
        "organization": "CRVR registry operations",
        "role": Role.REGISTRY_STAFF,
    },
    {
        "email": "buyer@crvr.local",
        "full_name": "Maya Lindqvist",
        "organization": "Nordic Airways sustainability",
        "role": Role.BUYER,
    },
    {
        "email": "admin@crvr.local",
        "full_name": "Kittipong Rattana",
        "organization": "CRVR registry operations",
        "role": Role.ADMIN,
    },
]


def _ensure_demo_seeding_allowed() -> None:
    settings = get_settings()
    if settings.is_production and not settings.demo_mode:
        raise RuntimeError(
            "Demo data seeding is disabled when APP_ENV=production (unless DEMO_MODE=true)"
        )


def seed_demo_users(db: Session | None = None) -> int:
    """Create the demo accounts that do not exist yet. Uses `db` when given (the demo reset)."""
    _ensure_demo_seeding_allowed()
    if db is None:
        with SessionLocal() as session:
            return seed_demo_users(session)
    created = 0
    password_hash = hash_password(get_settings().demo_password)
    for data in DEMO_USERS:
        if db.scalar(select(User).where(User.email == data["email"])):
            continue
        db.add(User(**data, password_hash=password_hash))
        created += 1
    db.commit()
    return created


def seed_demo_data(db: Session | None = None) -> str:
    """Accounts, projects, boundaries and verification assignments. Uses `db` when given."""
    _ensure_demo_seeding_allowed()
    if db is None:
        with SessionLocal() as session:
            return seed_demo_data(session)
    # Imported here: feature modules import app.auth, whose router imports DEMO_USERS from here.
    from app.features.boundary.seed import seed_demo_boundaries
    from app.features.registration.seed import seed_demo_projects
    from app.features.verification.seed import seed_demo_assignments

    users = seed_demo_users(db)
    projects = seed_demo_projects(db)
    boundaries = seed_demo_boundaries(db)
    assignments = seed_demo_assignments(db)
    return (
        f"{users} user(s), {projects} project(s), {boundaries} boundary(ies), "
        f"{assignments} assignment(s)"
    )


if __name__ == "__main__":
    settings = get_settings()
    if settings.demo_enabled:
        created = seed_demo_data()
        # Never print a private (production demo) password into the logs.
        password = settings.demo_password if settings.demo_password_is_public else "(private)"
        print(f"seed: created {created} — demo password: {password}")
