"""F5 Security & auditability — API routes, mounted under /api/ledger."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.db import get_db
from app.features.audit.ledger import verify_ledger_chain
from app.features.audit.models import LedgerEntry
from app.features.audit.schemas import LedgerPageOut, LedgerVerificationOut

router = APIRouter(prefix="/ledger", tags=["F5 audit"])


@router.get("", response_model=LedgerPageOut)
def list_ledger_entries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.VERIFIER, Role.REGISTRY_STAFF, Role.BUYER, Role.ADMIN)),
) -> LedgerPageOut:
    """Return one page of audit ledger entries, newest first."""
    total = db.scalar(select(func.count()).select_from(LedgerEntry)) or 0
    items = db.scalars(
        select(LedgerEntry)
        .order_by(LedgerEntry.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return LedgerPageOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/verify", response_model=LedgerVerificationOut)
def verify_ledger(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.VERIFIER, Role.REGISTRY_STAFF, Role.BUYER, Role.ADMIN)),
) -> dict:
    """Cryptographically verify the integrity of the entire ledger chain."""
    valid, err = verify_ledger_chain(db)
    return {"valid": valid, "error": err}
