"""Demo verification queue for local development, using the mock-up's projects.

Assignment states follow F1's seeded project status: the submitted project is in review, and the
verified/issued ones carry a finished sign-off and approval, so the queue and the project
dashboard never disagree.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.features.registration.models import Project
from app.features.verification.models import (
    CHECKLIST,
    Approval,
    ApprovalDecision,
    AssignmentStatus,
    ReportDecision,
    VerificationAssignment,
    VerificationReport,
)

# code, days from today (negative = overdue), status — must match the project's F1 status
DEMO_ASSIGNMENTS = [
    ("CRVR-0147", -4, AssignmentStatus.IN_REVIEW),  # submitted
    ("CRVR-0131", -40, AssignmentStatus.APPROVED),  # verified
    ("CRVR-0092", -90, AssignmentStatus.APPROVED),  # verified
    ("CRVR-0088", -150, AssignmentStatus.APPROVED),  # issued
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
        if status == AssignmentStatus.APPROVED:
            signed_at = datetime.now(UTC) + timedelta(days=offset - 3)
            report = VerificationReport(
                assignment_id=assignment.id,
                verifier_id=verifier.id,
                checklist=[{"key": key, "checked": True} for key, _label in CHECKLIST],
                note="Boundary is clear and the project record matches the applicant.",
                decision=ReportDecision.SIGN_OFF,
                signed_at=signed_at,
            )
            db.add(report)
            db.flush()
            # Maker-checker: staff approve; they are neither the verifier nor the owner
            db.add(
                Approval(
                    report_id=report.id,
                    approver_id=staff.id,
                    decision=ApprovalDecision.APPROVED,
                    rationale="Checklist complete and the boundary is clear.",
                    decided_at=signed_at + timedelta(days=1),
                )
            )
        created += 1
    db.commit()
    return created
