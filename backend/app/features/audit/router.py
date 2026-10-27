"""F5 Security & auditability — API routes, mounted under /api/ledger."""

from fastapi import APIRouter, Depends

from app.auth.deps import require_roles
from app.auth.models import Role, User

router = APIRouter(prefix="/ledger", tags=["F5 audit"])


@router.get("")
def list_ledger_entries(
    user: User = Depends(require_roles(Role.VERIFIER, Role.REGISTRY_STAFF, Role.BUYER, Role.ADMIN)),
) -> list[dict]:
    """Audit ledger entries, newest first. Placeholder until F5 is built."""
    return []
