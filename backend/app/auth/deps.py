from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import decode_access_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the signed-in user from the session cookie, or reject with 401."""
    token = request.cookies.get(get_settings().session_cookie)
    user_id = decode_access_token(token) if token else None
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    """Route dependency that only lets the given roles through.

    Usage: `user: User = Depends(require_roles(Role.VERIFIER, Role.ADMIN))`
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
        return user

    return checker
