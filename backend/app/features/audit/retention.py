"""Retention for the security log (#35): events are kept for 90 days, then deleted.

The ledger is kept forever and cannot be deleted (append-only trigger). Evidence is kept for 7
years by the production bucket's retention lock (#20). Only security events expire here.

Deletion runs every time a security event is recorded, so the policy holds without a scheduler.
It can also be run by hand or from a scheduled job:

    docker compose exec backend python -m app.features.audit.retention
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.features.audit.models import SecurityEvent

SECURITY_EVENT_RETENTION = timedelta(days=90)


def purge_expired_security_events(db: Session, *, now: datetime | None = None) -> int:
    """Delete security events older than the retention period; returns how many."""
    cutoff = (now or datetime.now(UTC)) - SECURITY_EVENT_RETENTION
    result = db.execute(delete(SecurityEvent).where(SecurityEvent.created_at < cutoff))
    return result.rowcount or 0


if __name__ == "__main__":
    from app.core.db import SessionLocal
    from app.core.models_registry import import_all_models

    import_all_models()
    with SessionLocal.begin() as session:
        deleted = purge_expired_security_events(session)
    print(f"Deleted {deleted} security events older than {SECURITY_EVENT_RETENTION.days} days.")
