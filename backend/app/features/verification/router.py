"""F3 Verification workflow — API routes, mounted under /api/verifications."""

from fastapi import APIRouter, Depends

from app.auth.deps import require_roles
from app.auth.models import Role, User

router = APIRouter(prefix="/verifications", tags=["F3 verification"])


@router.get("/queue")
def verification_queue(
    user: User = Depends(require_roles(Role.VERIFIER, Role.REGISTRY_STAFF, Role.ADMIN)),
) -> list[dict]:
    """The verifier's queue of assigned projects. Placeholder until F3 is built."""
    return []
