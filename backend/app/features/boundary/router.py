"""F2 Geospatial boundary & overlap detection — API routes, mounted under /api/boundaries."""

from fastapi import APIRouter, Depends

from app.auth.deps import require_roles
from app.auth.models import Role, User

router = APIRouter(prefix="/boundaries", tags=["F2 boundary"])


@router.get("")
def list_boundaries(
    user: User = Depends(
        require_roles(Role.DEVELOPER, Role.VERIFIER, Role.REGISTRY_STAFF, Role.ADMIN)
    ),
) -> list[dict]:
    """Registered boundaries and their overlap results. Placeholder until F2 is built."""
    return []
