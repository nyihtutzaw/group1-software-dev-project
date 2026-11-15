"""Admin-only user management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.admin_service import create_user, list_users, update_user
from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.auth.schemas import AdminUserCreate, AdminUserOut, AdminUserUpdate
from app.core.db import get_db

router = APIRouter(prefix="/admin/users", tags=["F5 user management"])


@router.get("", response_model=list[AdminUserOut])
def get_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(Role.ADMIN)),
) -> list[User]:
    return list_users(db)


@router.post("", response_model=AdminUserOut, status_code=201)
def post_user(
    body: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
) -> User:
    return create_user(db, admin, body)


@router.patch("/{user_id}", response_model=AdminUserOut)
def patch_user(
    user_id: int,
    body: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
) -> User:
    return update_user(db, admin, user_id, body)
