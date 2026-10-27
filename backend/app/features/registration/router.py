"""F1 Project registration & evidence — API routes, mounted under /api/projects."""

from fastapi import APIRouter, Depends

from app.auth.deps import require_roles
from app.auth.models import Role, User

router = APIRouter(prefix="/projects", tags=["F1 registration"])


@router.get("")
def list_projects(
    user: User = Depends(require_roles(Role.DEVELOPER, Role.REGISTRY_STAFF, Role.ADMIN)),
) -> list[dict]:
    """Developers see their projects; staff see all. Placeholder until F1 is built."""
    return []
