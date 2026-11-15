from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.auth.models import Role
from app.core.config import get_settings
from app.features.audit.models import SecurityEvent
from app.features.audit.security_log import (
    FAILED_SIGN_IN,
    SIGN_IN_LOCKOUT,
    SIGN_IN_RATE_LIMITED,
    hash_login_subject,
)
from tests.conftest import PASSWORD


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_login_sets_session_cookie_and_me_returns_user(client, make_user):
    user = make_user(Role.VERIFIER)

    res = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})

    assert res.status_code == 200
    assert "crvr_session" in res.cookies
    me = client.get("/api/auth/me").json()
    assert me["email"] == user.email
    assert me["role"] == "verifier"


def test_login_cookie_is_secure_in_production(client, make_user, monkeypatch):
    user = make_user(Role.VERIFIER)
    monkeypatch.setattr(get_settings(), "app_env", "production")

    res = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})

    assert res.status_code == 200
    assert "; secure" in res.headers["set-cookie"].lower()


def test_login_rejects_wrong_password_and_records_security_event(client, make_user, db):
    user = make_user()

    res = client.post("/api/auth/login", json={"email": user.email, "password": "nope"})

    assert res.status_code == 401
    event = db.scalar(select(SecurityEvent).where(SecurityEvent.event_type == FAILED_SIGN_IN))
    assert event is not None
    assert event.actor_id == user.id
    assert event.subject_hash == hash_login_subject(user.email, get_settings().jwt_secret)
    assert event.source_ip == "testclient"
    assert event.status_code == 401


def test_login_records_unknown_email_without_storing_the_address(client, db):
    email = "unknown@example.test"

    res = client.post("/api/auth/login", json={"email": email, "password": "nope"})

    assert res.status_code == 401
    event = db.scalar(select(SecurityEvent).where(SecurityEvent.event_type == FAILED_SIGN_IN))
    assert event is not None
    assert event.actor_id is None
    assert event.subject_hash == hash_login_subject(email, get_settings().jwt_secret)
    assert event.subject_hash != email


def test_login_rejects_inactive_user(client, make_user, db):
    user = make_user()
    user.is_active = False
    db.flush()

    res = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})

    assert res.status_code == 401
    event = db.scalar(select(SecurityEvent).where(SecurityEvent.event_type == FAILED_SIGN_IN))
    assert event is not None
    assert event.actor_id == user.id


def test_login_temporarily_blocks_after_five_failures_and_expires(client, make_user, db):
    user = make_user()
    attempted_email = f"  {user.email.upper()}  "

    for _ in range(5):
        response = client.post(
            "/api/auth/login", json={"email": attempted_email, "password": "wrong"}
        )
        assert response.status_code == 401

    blocked = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0

    subject_hash = hash_login_subject(user.email, get_settings().jwt_secret)
    events = db.scalars(
        select(SecurityEvent).where(SecurityEvent.subject_hash == subject_hash)
    ).all()
    assert sum(event.event_type == FAILED_SIGN_IN for event in events) == 5
    assert sum(event.event_type == SIGN_IN_LOCKOUT for event in events) == 1
    assert sum(event.event_type == SIGN_IN_RATE_LIMITED for event in events) == 1

    past = datetime.now(UTC) - timedelta(minutes=16)
    for event in events:
        event.created_at = past
    db.flush()

    expired = client.post("/api/auth/login", json={"email": user.email, "password": "wrong"})
    assert expired.status_code == 401


def test_me_requires_sign_in(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client, login):
    login(Role.BUYER)

    client.post("/api/auth/logout")

    assert client.get("/api/auth/me").status_code == 401
