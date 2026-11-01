"""F3 Verification workflow — database tables."""

import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin

# Fixed checklist from the Verify mock-up. The source line for each item is filled in
# when a review is opened (overlap text comes from F2; evidence files wait on F1).
CHECKLIST: tuple[tuple[str, str], ...] = (
    ("land_title", "Land title matches applicant"),
    ("boundary_overlap", "Boundary has no overlap"),
    ("baseline", "Baseline evidence is complete"),
    ("methodology", "Methodology applied correctly"),
    ("site_visit", "Site visit completed"),
)


def _enum(cls: type[enum.StrEnum]) -> Enum:
    return Enum(
        cls,
        name=cls.__name__.lower(),
        native_enum=False,
        length=32,
        values_callable=lambda members: [member.value for member in members],
    )


class AssignmentStatus(enum.StrEnum):
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    SIGNED_OFF = "signed_off"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReportDecision(enum.StrEnum):
    SIGN_OFF = "sign_off"
    REQUEST_CHANGES = "request_changes"


class ApprovalDecision(enum.StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


# A finished approval is no longer waiting on the verifier's due date.
CLOSED = (AssignmentStatus.APPROVED, AssignmentStatus.REJECTED)


class VerificationAssignment(TimestampMixin, Base):
    """One verifier's assignment for a project. One row per project."""

    __tablename__ = "verification_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    verifier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[AssignmentStatus] = mapped_column(
        _enum(AssignmentStatus),
        default=AssignmentStatus.ASSIGNED,
        server_default=AssignmentStatus.ASSIGNED.value,
    )


class VerificationReport(TimestampMixin, Base):
    """A verifier's checklist and note. Sign-off is irreversible; request-changes is not."""

    __tablename__ = "verification_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("verification_assignments.id"), index=True
    )
    verifier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    note: Mapped[str] = mapped_column(Text)
    decision: Mapped[ReportDecision] = mapped_column(_enum(ReportDecision))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Approval(TimestampMixin, Base):
    """Registry staff decision on a sign-off. The maker cannot be the approver."""

    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("verification_reports.id"), unique=True)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    decision: Mapped[ApprovalDecision] = mapped_column(_enum(ApprovalDecision))
    rationale: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
