"""Explicit staff issuance after approval (#25), publishing through the existing F4 handoff.

One batch per approval. The staff request supplies the actual vintage, tonnes and public
country; a developer's estimated removal is never silently treated as issued tonnes.
"""

from datetime import UTC, datetime
from typing import Literal

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
    BUFFER_PERCENT,
    CHECKLIST,
    Approval,
    ApprovalDecision,
    AssignmentStatus,
    ReportDecision,
    RiskRating,
    VerificationAssignment,
    VerificationReport,
)
from app.features.verification.schemas import IssueIn


def _serial(code: str, vintage: int, approval_id: int, start: int, end: int) -> str:
    return f"{code}-{vintage}-A{approval_id:08d}-{start:09d}-{end:09d}"


def _split_buffer(quantity: int, rating: str) -> tuple[int, int, int]:
    percent = BUFFER_PERCENT[RiskRating(rating)]
    buffer = (quantity * percent + 50) // 100
    if buffer >= quantity:
        raise HTTPException(
            422, "Issued quantity is too small to leave a tradable credit after the buffer pool"
        )
    return quantity - buffer, buffer, percent


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
    if report.risk_rating is None:
        raise HTTPException(409, "The verifier must set a reversal risk rating before issuance")
    tradable_qty, buffer_qty, percent = _split_buffer(data.quantity, report.risk_rating)
    issued_at = datetime.now(UTC)
    verifier_name = verifier.organization or verifier.full_name
    # The approval PK makes the serial namespace unique. Units 1..tradable are sellable;
    # the rest of the issued range is the non-tradable buffer pool.
    with db.begin_nested():
        credit = _publish_batch(
            db,
            actor=actor,
            developer=developer,
            project=project,
            report=report,
            approval=approval,
            data=data,
            issued_at=issued_at,
            verifier_name=verifier_name,
            quantity=tradable_qty,
            start=1,
            end=tradable_qty,
            batch_status="active",
        )
        buffer = None
        if buffer_qty:
            buffer = _publish_batch(
                db,
                actor=actor,
                developer=developer,
                project=project,
                report=report,
                approval=approval,
                data=data,
                issued_at=issued_at,
                verifier_name=verifier_name,
                quantity=buffer_qty,
                start=tradable_qty + 1,
                end=data.quantity,
                batch_status="buffer",
            )
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
                "risk_rating": report.risk_rating,
                "buffer_percent": percent,
                "buffer_quantity": buffer_qty,
            },
        )
        if buffer is not None:
            record_action(
                db,
                actor=actor,
                action="credit.issued",
                entity="project",
                entity_id=project.id,
                payload={
                    "credit_id": buffer.id,
                    "approval_id": approval.id,
                    "serial": buffer.serial,
                    "vintage": buffer.vintage,
                    "quantity": buffer.quantity,
                    "status": "buffer",
                    "risk_rating": report.risk_rating,
                    "buffer_percent": percent,
                },
            )
    db.commit()
    return credit


def _publish_batch(
    db: Session,
    *,
    actor: User,
    developer: User,
    project: Project,
    report: VerificationReport,
    approval: Approval,
    data: IssueIn,
    issued_at: datetime,
    verifier_name: str,
    quantity: int,
    start: int,
    end: int,
    batch_status: Literal["active", "buffer"],
) -> RegistryCredit:
    credit = publish_credit(
        db,
        actor=actor,
        developer=developer,
        status=batch_status,
        data=PublicationIn(
            serial=_serial(project.code, data.vintage, approval.id, start, end),
            project_reference=project.code,
            project_name=project.name,
            country=data.country,
            methodology=project.methodology or "",
            vintage=data.vintage,
            quantity=quantity,
            verifier_name=verifier_name,
            verification_reference=f"VER-{report.id}",
            approval_reference=f"APP-{approval.id}",
            signed_off_at=report.signed_at,
            issued_at=issued_at,
        ),
    )
    credit.source_project_id = project.id
    credit.source_approval_id = approval.id
    return credit
