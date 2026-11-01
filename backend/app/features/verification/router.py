"""F3 Verification workflow — API routes, mounted under /api/verifications."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.db import get_db
from app.features.verification import service
from app.features.verification.schemas import (
    ApprovalIn,
    AssignIn,
    ChainOut,
    NoteOut,
    QueueItem,
    QueueOut,
    ReportIn,
    ReviewOut,
    VerifierOut,
)

router = APIRouter(prefix="/verifications", tags=["F3 verification"])

QUEUE_ROLES = (Role.VERIFIER, Role.REGISTRY_STAFF, Role.ADMIN)
STAFF_ROLES = (Role.REGISTRY_STAFF, Role.ADMIN)


@router.get("/queue", response_model=QueueOut)
def verification_queue(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*QUEUE_ROLES)),
) -> QueueOut:
    """Assigned projects, oldest due date first. A verifier sees only their own."""
    return service.queue(db, user)


@router.get("/verifiers", response_model=list[VerifierOut])
def verifiers(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*STAFF_ROLES)),
) -> list[VerifierOut]:
    """Active verifiers, so staff can assign one."""
    return service.list_verifiers(db)


@router.get("/notes", response_model=list[NoteOut])
def notes(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DEVELOPER)),
) -> list[NoteOut]:
    """Verifier notes on the developer's own projects after a request for changes."""
    return service.developer_notes(db, user)


@router.post("/assignments", response_model=QueueItem, status_code=status.HTTP_201_CREATED)
def create_assignment(
    body: AssignIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*STAFF_ROLES)),
) -> QueueItem:
    return service.assign(db, user, body)


@router.get("/assignments/{assignment_id}", response_model=ReviewOut)
def open_review(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*QUEUE_ROLES)),
) -> ReviewOut:
    return service.review(db, user, assignment_id)


@router.post("/assignments/{assignment_id}/report", response_model=ReviewOut)
def submit_report(
    assignment_id: int,
    body: ReportIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.VERIFIER)),
) -> ReviewOut:
    return service.submit_report(db, user, assignment_id, body)


@router.post("/reports/{report_id}/decision", response_model=ReviewOut)
def decide(
    report_id: int,
    body: ApprovalIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*STAFF_ROLES)),
) -> ReviewOut:
    return service.decide(db, user, report_id, body)


@router.get("/projects/{project_id}/chain", response_model=ChainOut)
def chain(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DEVELOPER, *QUEUE_ROLES)),
) -> ChainOut:
    """The full verification chain for one project."""
    return service.project_chain(db, user, project_id)
