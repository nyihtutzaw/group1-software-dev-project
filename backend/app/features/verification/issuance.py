"""Explicit staff issuance after approval (#25), publishing through the existing F4 handoff.

One batch per approval. The staff request supplies the actual vintage, tonnes and public
country; a developer's estimated removal is never silently treated as issued tonnes.
"""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.features.audit.ledger import record_action
from app.features.boundary.service import issuance_blocked
from app.features.registration.models import Project, ProjectStatus
from app.features.registry.models import RegistryCredit
from app.features.registry.schemas import PublicationIn
from app.features.registry.service import publish_credit
from app.features.verification.models import (
    CHECKLIST,
    Approval,
    ApprovalDecision,
    AssignmentStatus,
    ReportDecision,
    VerificationAssignment,
    VerificationReport,
)
from app.features.verification.schemas import IssueIn


def issue_credits(db: Session, actor: User, project_id: int, data: IssueIn) -> RegistryCredit:
    if not actor.is_active or actor.role not in (Role.REGISTRY_STAFF, Role.ADMIN):
        raise HTTPException(403, "Only registry staff can issue credits")
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.status != ProjectStatus.VERIFIED:
        raise HTTPException(409, "Only an approved, unissued project can issue credits")
    assignment = db.scalar(
        select(VerificationAssignment)
        .where(VerificationAssignment.project_id == project.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if assignment is None or assignment.status != AssignmentStatus.APPROVED:
        raise HTTPException(409, "An approved verification is required")
    report = db.scalar(
        select(VerificationReport)
        .where(VerificationReport.assignment_id == assignment.id)
        .order_by(VerificationReport.id.desc())
    )
    approval = (
        db.scalar(select(Approval).where(Approval.report_id == report.id)) if report else None
    )
    if (
        report is None
        or report.decision != ReportDecision.SIGN_OFF
        or approval is None
        or approval.decision != ApprovalDecision.APPROVED
    ):
        raise HTTPException(409, "The latest verification report must have staff approval")
    expected = {key for key, _label in CHECKLIST}
    checked = {item["key"] for item in report.checklist if item.get("checked") is True}
    if checked != expected:
        raise HTTPException(409, "The signed verification checklist must be complete")
    if actor.id in (project.owner_id, report.verifier_id) or approval.approver_id in (
        project.owner_id,
        report.verifier_id,
    ):
        raise HTTPException(403, "Issuance requires independent verification and registry staff")
    if reason := issuance_blocked(db, project.id):
        raise HTTPException(409, f"Issuance blocked: {reason}")
    if (
        project.methodology is None
        or project.crediting_start_year is None
        or project.crediting_end_year is None
    ):
        raise HTTPException(409, "Project methodology and crediting period are required")
    if not project.crediting_start_year <= data.vintage < project.crediting_end_year:
        raise HTTPException(422, "Vintage must fall within the project's crediting period")
    if data.vintage > datetime.now(UTC).year:
        raise HTTPException(422, "Future vintages cannot be issued")
    if db.scalar(select(RegistryCredit.id).where(RegistryCredit.source_approval_id == approval.id)):
        raise HTTPException(409, "This approval already has an issued credit batch")
    developer = db.get(User, project.owner_id)
    verifier = db.get(User, report.verifier_id)
    if developer is None or verifier is None:
        raise HTTPException(409, "Project developer or verifier is unavailable")
    # The approval PK makes the serial namespace unique; quantity is the inclusive range length.
    serial = f"{project.code}-{data.vintage}-A{approval.id:08d}-000000001-{data.quantity:09d}"
    with db.begin_nested():
        credit = publish_credit(
            db,
            actor=actor,
            developer=developer,
            data=PublicationIn(
                serial=serial,
                project_reference=project.code,
                project_name=project.name,
                country=data.country,
                methodology=project.methodology,
                vintage=data.vintage,
                quantity=data.quantity,
                verifier_name=verifier.organization or verifier.full_name,
                verification_reference=f"VER-{report.id}",
                approval_reference=f"APP-{approval.id}",
                signed_off_at=report.signed_at,
                issued_at=datetime.now(UTC),
            ),
        )
        credit.source_project_id = project.id
        credit.source_approval_id = approval.id
        project.status = ProjectStatus.ISSUED
        db.flush()
        record_action(
            db,
            actor=actor,
            action="credit.issued",
            entity="project",
            entity_id=project.id,
            payload={
                "credit_id": credit.id,
                "approval_id": approval.id,
                "serial": credit.serial,
                "vintage": credit.vintage,
                "quantity": credit.quantity,
            },
        )
    db.commit()
    return credit
