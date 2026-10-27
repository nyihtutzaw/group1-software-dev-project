from app.auth.models import Role
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


def test_login_rejects_wrong_password(client, make_user):
    user = make_user()

    res = client.post("/api/auth/login", json={"email": user.email, "password": "nope"})

    assert res.status_code == 401


def test_login_rejects_inactive_user(client, make_user, db):
    user = make_user()
    user.is_active = False
    db.flush()

    res = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})

    assert res.status_code == 401


def test_me_requires_sign_in(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client, login):
    login(Role.BUYER)

    client.post("/api/auth/logout")

    assert client.get("/api/auth/me").status_code == 401
