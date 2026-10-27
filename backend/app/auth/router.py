from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.auth.schemas import DemoAccount, LoginRequest, UserOut
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import create_access_token, verify_password
from app.seed import DEMO_USERS

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

    settings = get_settings()
    response.set_cookie(
        settings.session_cookie,
        create_access_token(user.id),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(get_settings().session_cookie)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/demo-accounts", response_model=list[DemoAccount])
def demo_accounts() -> list[dict]:
    """Quick-login list for the sign-in page. Empty unless demo users are seeded."""
    settings = get_settings()
    if settings.is_production or not settings.seed_demo_users:
        return []
    return DEMO_USERS
