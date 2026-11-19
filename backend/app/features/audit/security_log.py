"""Security-event logging and persistent sign-in throttling."""

import hashlib
import hmac
import math
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.features.audit.models import SecurityEvent
from app.features.audit.retention import purge_expired_security_events

FAILED_SIGN_IN = "failed_sign_in"
SIGN_IN_SUCCEEDED = "sign_in_succeeded"
SIGN_IN_LOCKOUT = "sign_in_lockout"
SIGN_IN_RATE_LIMITED = "sign_in_rate_limited"
ACCESS_DENIED = "access_denied"

LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = timedelta(minutes=15)
LOGIN_LOCKOUT_DURATION = timedelta(minutes=15)


def client_ip(request: Request) -> str:
    """Return the direct peer address; do not trust unconfigured forwarded headers."""
    return request.client.host if request.client else "unknown"


def hash_login_subject(email: str, secret: str) -> str:
    normalized_email = email.strip().lower()
    return hmac.new(secret.encode(), normalized_email.encode(), hashlib.sha256).hexdigest()


def lock_sign_in_pair(db: Session, *, subject_hash: str, source_ip: str) -> None:
    lock_key = f"crvr:login:{subject_hash}:{source_ip}"
    db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(lock_key, 0))))


def record_security_event(
    db: Session,
    *,
    event_type: str,
    source_ip: str,
    method: str,
    path: str,
    status_code: int,
    actor_id: int | None = None,
    subject_hash: str | None = None,
    created_at: datetime | None = None,
) -> SecurityEvent:
    # enforce the 90-day retention as events arrive (cheap: created_at is indexed)
    purge_expired_security_events(db)
    event = SecurityEvent(
        event_type=event_type,
        actor_id=actor_id,
        subject_hash=subject_hash,
        source_ip=source_ip[:45],
        method=method[:10],
        path=path[:255],
        status_code=status_code,
        created_at=created_at or datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    return event


def active_lockout_seconds(
    db: Session,
    *,
    subject_hash: str,
    source_ip: str,
    now: datetime,
) -> int:
    successful_sign_in = db.scalar(
        select(func.max(SecurityEvent.created_at)).where(
            SecurityEvent.event_type == SIGN_IN_SUCCEEDED,
            SecurityEvent.subject_hash == subject_hash,
            SecurityEvent.source_ip == source_ip,
        )
    )
    stmt = select(func.max(SecurityEvent.created_at)).where(
        SecurityEvent.event_type == SIGN_IN_LOCKOUT,
        SecurityEvent.subject_hash == subject_hash,
        SecurityEvent.source_ip == source_ip,
    )
    if successful_sign_in is not None:
        stmt = stmt.where(SecurityEvent.created_at > successful_sign_in)
    lockout_started = db.scalar(stmt)
    if lockout_started is None:
        return 0

    remaining = lockout_started + LOGIN_LOCKOUT_DURATION - now
    return max(0, math.ceil(remaining.total_seconds()))


def recent_failed_sign_in_count(
    db: Session,
    *,
    subject_hash: str,
    source_ip: str,
    now: datetime,
) -> int:
    window_start = now - LOGIN_FAILURE_WINDOW
    successful_sign_in = db.scalar(
        select(func.max(SecurityEvent.created_at)).where(
            SecurityEvent.event_type == SIGN_IN_SUCCEEDED,
            SecurityEvent.subject_hash == subject_hash,
            SecurityEvent.source_ip == source_ip,
        )
    )
    stmt = (
        select(func.count())
        .select_from(SecurityEvent)
        .where(
            SecurityEvent.event_type == FAILED_SIGN_IN,
            SecurityEvent.subject_hash == subject_hash,
            SecurityEvent.source_ip == source_ip,
            SecurityEvent.created_at >= window_start,
        )
    )
    if successful_sign_in is not None:
        stmt = stmt.where(SecurityEvent.created_at > successful_sign_in)
    return db.scalar(stmt) or 0
