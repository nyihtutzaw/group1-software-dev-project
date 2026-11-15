"""F5 Security & auditability — API routes, mounted under /api/ledger."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.db import get_db
from app.features.audit.ledger import verify_ledger_chain
from app.features.audit.models import LedgerEntry
from app.features.audit.schemas import LedgerEntryOut, LedgerVerificationOut

router = APIRouter(prefix="/ledger", tags=["F5 audit"])


@router.get("", response_model=list[LedgerEntryOut])
def list_ledger_entries(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.VERIFIER, Role.REGISTRY_STAFF, Role.BUYER, Role.ADMIN)),
) -> list[LedgerEntry]:
    """Audit ledger entries, newest first."""
    stmt = select(LedgerEntry).order_by(LedgerEntry.id.desc())
    return list(db.scalars(stmt).all())


@router.get("/verify", response_model=LedgerVerificationOut)
def verify_ledger(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.VERIFIER, Role.REGISTRY_STAFF, Role.ADMIN)),
) -> dict:
    """Cryptographically verify the integrity of the entire ledger chain."""
    valid, err = verify_ledger_chain(db)
    return {"valid": valid, "error": err}
