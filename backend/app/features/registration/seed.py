"""Demo projects for local development (names and IDs from the UI mock-up).

F1: replace or extend these when the registration fields exist.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.features.registration.models import Project

DEMO_PROJECTS = [
    # code, name, owner email, status, registered
    ("CRVR-0088", "Nan Valley Community Forest", "developer2@crvr.local", "issued", "2025-11-12"),
    ("CRVR-0092", "Phrae Agroforestry", "developer2@crvr.local", "verified", "2026-03-03"),
    ("CRVR-0131", "Chiang Rai Mangrove Restore", "developer@crvr.local", "verified", "2026-08-04"),
    ("CRVR-0147", "Nan Reforestation Phase II", "developer@crvr.local", "submitted", "2026-09-12"),
    ("CRVR-0156", "Phetchabun Agroforestry", "developer@crvr.local", "draft", "2026-10-01"),
]


def seed_demo_projects(db: Session) -> int:
    created = 0
    for code, name, owner_email, status, registered in DEMO_PROJECTS:
        if db.scalar(select(Project).where(Project.code == code)):
            continue
        owner = db.scalar(select(User).where(User.email == owner_email))
        if owner is None:
            continue
        db.add(
            Project(
                code=code,
                name=name,
                owner_id=owner.id,
                status=status,
                created_at=datetime.fromisoformat(registered).replace(tzinfo=UTC),
            )
        )
        created += 1
    db.commit()
    return created
