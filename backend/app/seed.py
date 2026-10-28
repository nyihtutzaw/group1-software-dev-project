"""Load demo data for local development: accounts (one per role), projects and boundaries.

Run with `python -m app.seed`. Safe to run repeatedly: existing records are left alone.
"""

from sqlalchemy import select

from app.auth.models import Role, User
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password

DEMO_PASSWORD = "crvr-demo"

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


def seed_demo_users() -> int:
    created = 0
    with SessionLocal() as db:
        for data in DEMO_USERS:
            if db.scalar(select(User).where(User.email == data["email"])):
                continue
            db.add(User(**data, password_hash=hash_password(DEMO_PASSWORD)))
            created += 1
        db.commit()
    return created


def seed_demo_data() -> str:
    # Imported here: feature modules import app.auth, whose router imports DEMO_USERS from here.
    from app.features.boundary.seed import seed_demo_boundaries
    from app.features.registration.seed import seed_demo_projects

    users = seed_demo_users()
    with SessionLocal() as db:
        projects = seed_demo_projects(db)
        boundaries = seed_demo_boundaries(db)
    return f"{users} user(s), {projects} project(s), {boundaries} boundary(ies)"


if __name__ == "__main__":
    settings = get_settings()
    if settings.seed_demo_users and not settings.is_production:
        print(f"seed: created {seed_demo_data()} — demo password: {DEMO_PASSWORD}")
