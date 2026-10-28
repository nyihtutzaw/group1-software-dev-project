"""F4 public registry reads and role-filtered evidence summaries."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.auth.models import Role, User
from app.core.config import get_settings
from app.core.db import get_db
from app.features.registry import service
from app.features.registry.models import RegistryCreditEvent
from app.features.registry.schemas import (
    CreditDetail,
    CreditEventOut,
    CreditOut,
    CreditPage,
    EvidenceOut,
    EvidencePackOut,
    IntegrityOut,
)

router = APIRouter(prefix="/registry", tags=["F4 registry"])


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    # Anonymous requests are public; invalid/inactive sessions must not bypass buyer filtering.
    if not request.cookies.get(get_settings().session_cookie):
        return None
    return get_current_user(request, db)


@router.get("/credits", response_model=CreditPage)
def list_credits(
    q: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> CreditPage:
    return service.list_credits(db, user=user, q=q, page=page, page_size=page_size)


@router.get("/credits/{credit_id}", response_model=CreditDetail)
def credit_detail(
    credit_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> CreditDetail:
    credit = service.get_credit(db, credit_id, user)
    history = db.scalars(
        select(RegistryCreditEvent)
        .where(RegistryCreditEvent.credit_id == credit.id)
        .order_by(RegistryCreditEvent.occurred_at, RegistryCreditEvent.id)
    ).all()
    return CreditDetail(
        **CreditOut.model_validate(credit).model_dump(),
        history=[CreditEventOut.model_validate(event) for event in history],
    )


@router.get("/credits/{credit_id}/evidence", response_model=EvidencePackOut)
def credit_evidence(
    credit_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.BUYER, Role.REGISTRY_STAFF, Role.ADMIN)),
) -> EvidencePackOut:
    credit, items = service.evidence_pack(db, credit_id, user)
    return EvidencePackOut(
        serial=credit.serial, items=[EvidenceOut.model_validate(item) for item in items]
    )


@router.get("/credits/{credit_id}/integrity", response_model=IntegrityOut)
def credit_integrity(
    credit_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> IntegrityOut:
    credit = service.get_credit(db, credit_id, user)
    return IntegrityOut(snapshot_matches=credit.snapshot_sha256 == service.snapshot_digest(credit))
