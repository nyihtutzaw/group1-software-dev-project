"""F1 Project registration & evidence — API routes, mounted under /api/projects."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.db import get_db
from app.features.registration.models import Project
from app.features.registration.schemas import ProjectOut

router = APIRouter(prefix="/projects", tags=["F1 registration"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DEVELOPER, Role.REGISTRY_STAFF, Role.ADMIN)),
) -> Sequence[Project]:
    """Developers see their own projects; registry staff and admins see all."""
    stmt = select(Project).order_by(Project.code)
    if user.role == Role.DEVELOPER:
        stmt = stmt.where(Project.owner_id == user.id)
    return db.scalars(stmt).all()
