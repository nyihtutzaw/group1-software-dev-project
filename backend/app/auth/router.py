from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.auth.schemas import DemoAccount, LoginRequest, UserOut
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import create_access_token, verify_password
from app.features.audit.security_log import (
    FAILED_SIGN_IN,
    LOGIN_FAILURE_LIMIT,
    SIGN_IN_LOCKOUT,
    SIGN_IN_RATE_LIMITED,
    SIGN_IN_SUCCEEDED,
    active_lockout_seconds,
    client_ip,
    hash_login_subject,
    lock_sign_in_pair,
    recent_failed_sign_in_count,
    record_security_event,
)
from app.seed import DEMO_USERS

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    normalized_email = body.email.strip().lower()
    source_ip = client_ip(request)
    subject_hash = hash_login_subject(normalized_email, settings.jwt_secret)
    now = datetime.now(UTC)

    lock_sign_in_pair(db, subject_hash=subject_hash, source_ip=source_ip)
    retry_after = active_lockout_seconds(
        db, subject_hash=subject_hash, source_ip=source_ip, now=now
    )
    if retry_after:
        record_security_event(
            db,
            event_type=SIGN_IN_RATE_LIMITED,
            subject_hash=subject_hash,
            source_ip=source_ip,
            method=request.method,
            path=request.url.path,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            created_at=now,
        )
        db.commit()
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many sign-in attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        record_security_event(
            db,
            event_type=FAILED_SIGN_IN,
            actor_id=user.id if user else None,
            subject_hash=subject_hash,
            source_ip=source_ip,
            method=request.method,
            path=request.url.path,
            status_code=status.HTTP_401_UNAUTHORIZED,
            created_at=now,
        )
        if (
            recent_failed_sign_in_count(db, subject_hash=subject_hash, source_ip=source_ip, now=now)
            >= LOGIN_FAILURE_LIMIT
        ):
            record_security_event(
                db,
                event_type=SIGN_IN_LOCKOUT,
                actor_id=user.id if user else None,
                subject_hash=subject_hash,
                source_ip=source_ip,
                method=request.method,
                path=request.url.path,
                status_code=status.HTTP_401_UNAUTHORIZED,
                created_at=now,
            )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

    record_security_event(
        db,
        event_type=SIGN_IN_SUCCEEDED,
        actor_id=user.id,
        subject_hash=subject_hash,
        source_ip=source_ip,
        method=request.method,
        path=request.url.path,
        status_code=status.HTTP_200_OK,
        created_at=now,
    )
    db.commit()
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
