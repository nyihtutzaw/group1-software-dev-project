"""Admin-only user management operations."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.auth.schemas import AdminUserCreate, AdminUserUpdate
from app.core.security import hash_password
from app.features.audit.ledger import record_action


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


def create_user(db: Session, actor: User, data: AdminUserCreate) -> User:
    email = str(data.email)
    existing = db.scalar(select(User.id).where(func.lower(User.email) == email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        email=email,
        full_name=data.full_name,
        organization=data.organization,
        role=data.role,
        password_hash=hash_password(data.initial_password),
    )
    db.add(user)
    db.flush()
    record_action(
        db,
        actor=actor,
        action="user.created",
        entity="user",
        entity_id=user.id,
        payload={"email": user.email, "role": user.role.value},
    )
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, actor: User, user_id: int, data: AdminUserUpdate) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    changes = data.model_dump(exclude_unset=True)
    if user.id == actor.id and (
        changes.get("role", user.role) != user.role
        or changes.get("is_active", user.is_active) is False
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You cannot change your own role or deactivate your account"
        )

    next_role = changes.get("role", user.role)
    next_active = changes.get("is_active", user.is_active)
    if user.role == Role.ADMIN and user.is_active and (next_role != Role.ADMIN or not next_active):
        active_admin_ids = db.scalars(
            select(User.id)
            .where(User.role == Role.ADMIN, User.is_active.is_(True))
            .order_by(User.id)
            .with_for_update()
        ).all()
        if len(active_admin_ids) <= 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "The last active admin account cannot be changed"
            )

    role_changed = next_role != user.role
    active_changed = next_active != user.is_active
    if not role_changed and not active_changed:
        return user

    previous_role = user.role
    user.role = next_role
    user.is_active = next_active
    db.flush()

    if role_changed:
        record_action(
            db,
            actor=actor,
            action="user.role_changed",
            entity="user",
            entity_id=user.id,
            payload={"email": user.email, "from": previous_role.value, "to": user.role.value},
        )
    if active_changed:
        record_action(
            db,
            actor=actor,
            action="user.activated" if user.is_active else "user.deactivated",
            entity="user",
            entity_id=user.id,
            payload={"email": user.email},
        )

    db.commit()
    db.refresh(user)
    return user
