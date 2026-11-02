"""Demo verification queue for local development, using the mock-up's projects."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.features.registration.models import Project
from app.features.verification.models import (
    CHECKLIST,
    AssignmentStatus,
    ReportDecision,
    VerificationAssignment,
    VerificationReport,
)

# code, days from today (negative = overdue), status
DEMO_ASSIGNMENTS = [
    ("CRVR-0147", -4, AssignmentStatus.IN_REVIEW),
    ("CRVR-0131", -12, AssignmentStatus.ASSIGNED),
    ("CRVR-0092", 20, AssignmentStatus.ASSIGNED),
    ("CRVR-0088", 5, AssignmentStatus.SIGNED_OFF),
]


def seed_demo_assignments(db: Session) -> int:
    verifier = db.scalar(select(User).where(User.email == "verifier@crvr.local"))
    staff = db.scalar(select(User).where(User.email == "staff@crvr.local"))
    if verifier is None or staff is None:
        return 0
    today = datetime.now(UTC).date()
    created = 0
    for code, offset, status in DEMO_ASSIGNMENTS:
        project = db.scalar(select(Project).where(Project.code == code))
        if project is None:
            continue
        if db.scalar(
            select(VerificationAssignment).where(VerificationAssignment.project_id == project.id)
        ):
            continue
        assignment = VerificationAssignment(
            project_id=project.id,
            verifier_id=verifier.id,
            assigned_by_id=staff.id,
            due_date=today + timedelta(days=offset),
            status=status,
        )
        db.add(assignment)
        db.flush()
        if status == AssignmentStatus.SIGNED_OFF:
            db.add(
                VerificationReport(
                    assignment_id=assignment.id,
                    verifier_id=verifier.id,
                    checklist=[{"key": key, "checked": True} for key, _label in CHECKLIST],
                    note="Boundary is clear and the project record matches the applicant.",
                    decision=ReportDecision.SIGN_OFF,
                    signed_at=datetime.now(UTC),
                )
            )
        created += 1
    db.commit()
    return created
