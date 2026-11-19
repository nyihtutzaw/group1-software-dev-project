"""#35 — security events are deleted after 90 days; the ledger is never touched."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.auth.models import Role
from app.features.audit.ledger import record_action
from app.features.audit.models import LedgerEntry, SecurityEvent
from app.features.audit.retention import purge_expired_security_events
from app.features.audit.security_log import ACCESS_DENIED, record_security_event

NOW = datetime(2026, 11, 19, 12, tzinfo=UTC)


def add_event(db, age: timedelta) -> SecurityEvent:
    event = SecurityEvent(
        event_type=ACCESS_DENIED,
        source_ip="203.0.113.7",
        method="GET",
        path="/api/ledger",
        status_code=403,
        created_at=NOW - age,
    )
    db.add(event)
    db.flush()
    return event


def remaining(db) -> set[int]:
    return set(db.scalars(select(SecurityEvent.id)))


def test_purge_deletes_only_events_older_than_90_days(db):
    old = add_event(db, timedelta(days=91))
    edge = add_event(db, timedelta(days=90))  # exactly 90 days old is still kept
    recent = add_event(db, timedelta(days=1))

    assert purge_expired_security_events(db, now=NOW) == 1
    assert remaining(db) == {edge.id, recent.id}
    assert old.id not in remaining(db)


def test_recording_an_event_enforces_retention(db):
    old = add_event(db, timedelta(days=400))

    new = record_security_event(
        db,
        event_type=ACCESS_DENIED,
        source_ip="203.0.113.7",
        method="GET",
        path="/api/admin/users",
        status_code=403,
    )

    assert remaining(db) == {new.id}
    assert old.id not in remaining(db)


def test_purge_never_touches_the_ledger(db, make_user):
    record_action(
        db,
        actor=make_user(Role.DEVELOPER),
        action="project.created",
        entity="project",
        entity_id=1,
    )
    before = db.scalar(select(func.count()).select_from(LedgerEntry))
    add_event(db, timedelta(days=365))

    purge_expired_security_events(db, now=NOW + timedelta(days=3650))

    assert db.scalar(select(func.count()).select_from(LedgerEntry)) == before
