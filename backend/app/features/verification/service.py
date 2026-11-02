"""F3 business logic: assign, review, sign off, and maker-checker approval."""

from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.features.audit.ledger import record_action
from app.features.boundary.geometry import count_other_boundaries
from app.features.boundary.service import issuance_blocked
from app.features.registration.models import EvidenceFile, Project, ProjectStatus
from app.features.verification.models import (
    CHECKLIST,
    CLOSED,
    Approval,
    ApprovalDecision,
    AssignmentStatus,
    ReportDecision,
    VerificationAssignment,
    VerificationReport,
)
from app.features.verification.schemas import (
    ApprovalIn,
    ApprovalOut,
    AssignIn,
    AutoCheck,
    ChainEvent,
    ChainOut,
    CheckLine,
    ChipTone,
    EvidenceLine,
    NoteOut,
    QueueItem,
    QueueOut,
    ReportIn,
    ReviewOut,
    VerifierOut,
)

STAFF = (Role.REGISTRY_STAFF, Role.ADMIN)
OPEN_FOR_REPORT = (
    AssignmentStatus.ASSIGNED,
    AssignmentStatus.IN_REVIEW,
    AssignmentStatus.CHANGES_REQUESTED,
)


def _today() -> date:
    return datetime.now(UTC).date()


def _user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def _project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


def _assignment(db: Session, assignment_id: int) -> VerificationAssignment:
    row = db.get(VerificationAssignment, assignment_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    return row


def _latest_report(db: Session, assignment_id: int) -> VerificationReport | None:
    return db.scalar(
        select(VerificationReport)
        .where(VerificationReport.assignment_id == assignment_id)
        .order_by(VerificationReport.id.desc())
    )


def _reports(db: Session, assignment_id: int) -> list[VerificationReport]:
    return list(
        db.scalars(
            select(VerificationReport)
            .where(VerificationReport.assignment_id == assignment_id)
            .order_by(VerificationReport.id)
        )
    )


def _approval_for(db: Session, report_id: int) -> Approval | None:
    return db.scalar(select(Approval).where(Approval.report_id == report_id))


def _require_reader(user: User, assignment: VerificationAssignment) -> None:
    if user.role in STAFF:
        return
    if user.role == Role.VERIFIER and assignment.verifier_id == user.id:
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "This assignment is not yours")


def _overlap_detail(db: Session, project_id: int) -> tuple[bool, str]:
    reason = issuance_blocked(db, project_id)
    others = count_other_boundaries(db, exclude_project_id=project_id)
    if reason is None:
        return True, f"Auto-checked · no blocking overlap · {others} other boundaries"
    return False, f"Auto-checked · {reason}"


def _sources(db: Session, project_id: int) -> dict[str, str]:
    _passed, overlap = _overlap_detail(db, project_id)
    return {
        "land_title": "Deed on the project file · checked against the land-title extract",
        "boundary_overlap": overlap,
        "baseline": "Field survey and geo-tagged photos — evidence files are not stored yet",
        "methodology": "Methodology, growth curve and buffer pool on the registration",
        "site_visit": "Scheduled by the verifier · the visit itself stays a human activity",
    }


def _checked_map(report: VerificationReport | None) -> dict[str, bool]:
    if report is None:
        return {key: False for key, _label in CHECKLIST}
    return {item["key"]: bool(item["checked"]) for item in report.checklist}


def _chip(assignment: VerificationAssignment, today: date) -> tuple[bool, int, str, ChipTone]:
    overdue = assignment.due_date < today and assignment.status not in CLOSED
    days = (today - assignment.due_date).days if overdue else 0
    if overdue:
        return overdue, days, "OVERDUE", "warn"
    labels: dict[AssignmentStatus, tuple[str, ChipTone]] = {
        AssignmentStatus.ASSIGNED: ("NEW", "accent"),
        AssignmentStatus.IN_REVIEW: ("IN REVIEW", "wait"),
        AssignmentStatus.CHANGES_REQUESTED: ("IN REVIEW", "wait"),
        AssignmentStatus.SIGNED_OFF: ("SIGNED OFF", "wait"),
        AssignmentStatus.APPROVED: ("APPROVED", "ok"),
        AssignmentStatus.REJECTED: ("REJECTED", "warn"),
    }
    chip, tone = labels[assignment.status]
    return overdue, days, chip, tone


def _item(
    db: Session, assignment: VerificationAssignment, project: Project, today: date
) -> QueueItem:
    overdue, days, chip, tone = _chip(assignment, today)
    return QueueItem(
        id=assignment.id,
        project_id=project.id,
        project_code=project.code,
        project_name=project.name,
        verifier_name=_user(db, assignment.verifier_id).full_name,
        due_date=assignment.due_date,
        overdue=overdue,
        days_overdue=days,
        status=assignment.status,
        chip=chip,
        chip_tone=tone,
    )


def _chain(db: Session, assignment: VerificationAssignment, project: Project) -> list[ChainEvent]:
    assigner = _user(db, assignment.assigned_by_id)
    verifier = _user(db, assignment.verifier_id)
    events = [
        ChainEvent(
            id=f"assigned-{assignment.id}",
            kind="assigned",
            at=assignment.created_at,
            actor_name=assigner.full_name,
            summary=f"Assigned to {verifier.full_name} · due {assignment.due_date.isoformat()}",
        )
    ]
    for report in _reports(db, assignment.id):
        maker = _user(db, report.verifier_id)
        signed = report.decision == ReportDecision.SIGN_OFF
        events.append(
            ChainEvent(
                id=f"report-{report.id}",
                kind="report",
                at=report.signed_at,
                actor_name=maker.full_name,
                summary="Signed off" if signed else "Requested changes",
                note=report.note,
            )
        )
        approval = _approval_for(db, report.id)
        if approval is not None:
            approver = _user(db, approval.approver_id)
            events.append(
                ChainEvent(
                    id=f"approval-{approval.id}",
                    kind="approval",
                    at=approval.decided_at,
                    actor_name=approver.full_name,
                    summary="Approved"
                    if approval.decision == ApprovalDecision.APPROVED
                    else "Rejected",
                    note=approval.rationale,
                )
            )
    events.sort(key=lambda event: (event.at, event.id))
    return events


def _approval_out(db: Session, approval: Approval | None) -> ApprovalOut | None:
    if approval is None:
        return None
    return ApprovalOut(
        id=approval.id,
        decision=approval.decision,
        rationale=approval.rationale,
        approver_name=_user(db, approval.approver_id).full_name,
        decided_at=approval.decided_at,
    )


def _decision_block(
    user: User,
    assignment: VerificationAssignment,
    project: Project,
    report: VerificationReport | None,
    approval: Approval | None,
) -> str | None:
    if user.role not in STAFF or report is None or report.decision != ReportDecision.SIGN_OFF:
        return None
    if approval is not None:
        return None
    if user.id == report.verifier_id:
        return "You signed this off, so a different registry staff member must approve it."
    if user.id == project.owner_id:
        return "You submitted this project, so a different registry staff member must approve it."
    return None


def _evidence_lines(db: Session, project_id: int) -> list[EvidenceLine]:
    """F1's sealed uploads, with the hash the verifier can compare against the ledger."""
    files = db.scalars(
        select(EvidenceFile).where(EvidenceFile.project_id == project_id).order_by(EvidenceFile.id)
    ).all()
    if not files:
        return [EvidenceLine(title="Evidence files", detail="No files uploaded yet.")]
    return [
        EvidenceLine(
            title=f"{f.kind.value.replace('_', ' ').capitalize()} · {f.filename}",
            detail=f"sealed {f.sealed_at:%d %b %Y} · SHA-256 {f.sha256[:12]}…",
        )
        for f in files
    ]


def _review(
    db: Session, user: User, assignment: VerificationAssignment, project: Project
) -> ReviewOut:
    today = _today()
    report = _latest_report(db, assignment.id)
    approval = _approval_for(db, report.id) if report else None
    passed, overlap = _overlap_detail(db, project.id)
    checked = _checked_map(report)
    sources = _sources(db, project.id)
    can_submit = user.role == Role.VERIFIER and assignment.status in OPEN_FOR_REPORT
    can_submit = can_submit and assignment.verifier_id == user.id
    can_submit = can_submit and project.status == ProjectStatus.SUBMITTED
    block = _decision_block(user, assignment, project, report, approval)
    can_decide = (
        user.role in STAFF
        and report is not None
        and report.decision == ReportDecision.SIGN_OFF
        and approval is None
        and block is None
    )
    return ReviewOut(
        item=_item(db, assignment, project, today),
        evidence=[
            EvidenceLine(
                title="Project record",
                detail=f"{project.code} · {project.name} · status {project.status}",
            ),
            *_evidence_lines(db, project.id),
        ],
        automatic_checks=[AutoCheck(name="Boundary overlap", passed=passed, detail=overlap)],
        checklist=[
            CheckLine(key=key, label=label, source=sources[key], checked=checked.get(key, False))
            for key, label in CHECKLIST
        ],
        note=report.note if report else "",
        can_submit=can_submit,
        can_decide=can_decide,
        decision_block=block,
        report_id=report.id if report else None,
        approval=_approval_out(db, approval),
        chain=_chain(db, assignment, project),
    )


def list_verifiers(db: Session) -> list[VerifierOut]:
    rows = db.scalars(
        select(User)
        .where(User.role == Role.VERIFIER, User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return [VerifierOut(id=row.id, full_name=row.full_name, email=row.email) for row in rows]


def assign(db: Session, actor: User, data: AssignIn) -> QueueItem:
    project = _project(db, data.project_id)
    if project.status != ProjectStatus.SUBMITTED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Only a submitted project can be assigned for verification"
        )
    verifier = _user(db, data.verifier_id)
    if verifier.role != Role.VERIFIER or not verifier.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active verifier")
    existing = db.scalar(
        select(VerificationAssignment).where(VerificationAssignment.project_id == project.id)
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This project already has a verifier")
    row = VerificationAssignment(
        project_id=project.id,
        verifier_id=verifier.id,
        assigned_by_id=actor.id,
        due_date=data.due_date,
        status=AssignmentStatus.ASSIGNED,
    )
    db.add(row)
    db.flush()
    record_action(
        db,
        actor=actor,
        action="verification.assigned",
        entity="project",
        entity_id=project.id,
        payload={
            "assignment_id": row.id,
            "verifier_id": verifier.id,
            "due_date": data.due_date.isoformat(),
        },
    )
    db.commit()
    db.refresh(row)
    return _item(db, row, project, _today())


def queue(db: Session, user: User) -> QueueOut:
    today = _today()
    stmt = (
        select(VerificationAssignment, Project)
        .join(Project, Project.id == VerificationAssignment.project_id)
        .order_by(VerificationAssignment.due_date, VerificationAssignment.id)
    )
    if user.role == Role.VERIFIER:
        stmt = stmt.where(VerificationAssignment.verifier_id == user.id)
    rows = db.execute(stmt).all()
    items = [_item(db, assignment, project, today) for assignment, project in rows]
    year_start = datetime(today.year, 1, 1, tzinfo=UTC)
    signed = (
        select(func.count())
        .select_from(VerificationReport)
        .where(
            VerificationReport.decision == ReportDecision.SIGN_OFF,
            VerificationReport.signed_at >= year_start,
        )
    )
    if user.role == Role.VERIFIER:
        signed = signed.where(VerificationReport.verifier_id == user.id)
    return QueueOut(
        items=items,
        assigned_count=len(items),
        overdue_count=sum(1 for item in items if item.overdue),
        signed_off_this_year=db.scalar(signed) or 0,
    )


def review(db: Session, user: User, assignment_id: int) -> ReviewOut:
    assignment = _assignment(db, assignment_id)
    _require_reader(user, assignment)
    return _review(db, user, assignment, _project(db, assignment.project_id))


def submit_report(db: Session, user: User, assignment_id: int, data: ReportIn) -> ReviewOut:
    assignment = _assignment(db, assignment_id)
    if user.role != Role.VERIFIER or assignment.verifier_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the assigned verifier can submit")
    if assignment.status not in OPEN_FOR_REPORT:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Sign-off is irreversible and this review is already closed"
        )
    project = _project(db, assignment.project_id)
    if project.status != ProjectStatus.SUBMITTED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The developer is still making the requested changes and has not resubmitted",
        )
    note = data.note.strip()
    if not note:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Add a note")
    report = VerificationReport(
        assignment_id=assignment.id,
        verifier_id=user.id,
        checklist=[{"key": key, "checked": data.checklist[key]} for key, _label in CHECKLIST],
        note=note,
        decision=data.decision,
        signed_at=datetime.now(UTC),
    )
    if data.decision == ReportDecision.SIGN_OFF:
        assignment.status = AssignmentStatus.SIGNED_OFF
        action = "verification.signed_off"
    else:
        assignment.status = AssignmentStatus.CHANGES_REQUESTED
        # Back to the developer: F1 only allows edits and new evidence on a draft. Files already
        # sealed stay write-once; resubmitting seals the new set and the verifier reviews again.
        project.status = ProjectStatus.DRAFT
        project.submitted_at = None
        action = "verification.changes_requested"
    db.add(report)
    db.flush()
    record_action(
        db,
        actor=user,
        action=action,
        entity="project",
        entity_id=project.id,
        payload={"assignment_id": assignment.id, "report_id": report.id, "note": report.note},
    )
    db.commit()
    return _review(db, user, assignment, project)


def decide(db: Session, user: User, report_id: int, data: ApprovalIn) -> ReviewOut:
    report = db.get(VerificationReport, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if report.decision != ReportDecision.SIGN_OFF:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a sign-off can be approved or rejected")
    if _approval_for(db, report.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This sign-off already has a decision")
    assignment = _assignment(db, report.assignment_id)
    project = _project(db, assignment.project_id)
    if user.id == report.verifier_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You cannot approve a verification you signed off",
        )
    if user.id == project.owner_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You cannot approve a project you submitted",
        )
    rationale = data.rationale.strip()
    if len(rationale) < 5:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Add a rationale")
    approval = Approval(
        report_id=report.id,
        approver_id=user.id,
        decision=data.decision,
        rationale=rationale,
        decided_at=datetime.now(UTC),
    )
    assignment.status = (
        AssignmentStatus.APPROVED
        if data.decision == ApprovalDecision.APPROVED
        else AssignmentStatus.REJECTED
    )
    if data.decision == ApprovalDecision.APPROVED:
        project.status = ProjectStatus.VERIFIED
    db.add(approval)
    db.flush()
    record_action(
        db,
        actor=user,
        action=(
            "verification.approved"
            if data.decision == ApprovalDecision.APPROVED
            else "verification.rejected"
        ),
        entity="project",
        entity_id=project.id,
        payload={"report_id": report.id, "rationale": approval.rationale},
    )
    db.commit()
    return _review(db, user, assignment, project)


def project_chain(db: Session, user: User, project_id: int) -> ChainOut:
    project = _project(db, project_id)
    assignment = db.scalar(
        select(VerificationAssignment).where(VerificationAssignment.project_id == project.id)
    )
    if user.role == Role.DEVELOPER:
        if project.owner_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This project is not yours")
    elif user.role == Role.VERIFIER:
        if assignment is None or assignment.verifier_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This assignment is not yours")
    elif user.role not in STAFF:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
    return ChainOut(
        project_id=project.id,
        project_code=project.code,
        project_name=project.name,
        chain=_chain(db, assignment, project) if assignment else [],
    )


def developer_notes(db: Session, user: User) -> list[NoteOut]:
    projects = db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.code))
    notes: list[NoteOut] = []
    for project in projects:
        assignment = db.scalar(
            select(VerificationAssignment).where(VerificationAssignment.project_id == project.id)
        )
        if assignment is None or assignment.status != AssignmentStatus.CHANGES_REQUESTED:
            continue
        if project.status != ProjectStatus.DRAFT:
            continue  # already resubmitted — the note is answered
        report = _latest_report(db, assignment.id)
        if report is None or report.decision != ReportDecision.REQUEST_CHANGES:
            continue
        notes.append(
            NoteOut(
                project_id=project.id,
                project_code=project.code,
                project_name=project.name,
                note=report.note,
                at=report.signed_at,
            )
        )
    return notes
