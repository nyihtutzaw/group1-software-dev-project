from app.auth.models import Role, User
from app.core.security import verify_password


def test_admin_user_endpoints_require_admin(client, login):
    assert client.get("/api/admin/users").status_code == 401

    user_body = {
        "email": "new@example.com",
        "full_name": "New User",
        "role": "buyer",
        "initial_password": "a-long-initial-password",
    }
    for role in (Role.DEVELOPER, Role.VERIFIER, Role.REGISTRY_STAFF, Role.BUYER):
        login(role)
        assert client.get("/api/admin/users").status_code == 403
        assert client.post("/api/admin/users", json=user_body).status_code == 403
        assert client.patch("/api/admin/users/1", json={"is_active": False}).status_code == 403


def test_admin_can_list_users_without_credential_fields(client, login, make_user):
    login(Role.ADMIN)
    user = make_user(Role.DEVELOPER, email="dev@example.com")

    response = client.get("/api/admin/users")

    assert response.status_code == 200
    result = next(item for item in response.json() if item["id"] == user.id)
    assert result == {
        "id": user.id,
        "email": "dev@example.com",
        "full_name": "Test developer",
        "organization": None,
        "role": "developer",
        "is_active": True,
    }
    assert "password_hash" not in response.text


def test_admin_can_create_user_and_audit_without_password(client, login, db, monkeypatch):
    from app.auth import admin_service

    admin = login(Role.ADMIN)
    actions = []
    monkeypatch.setattr(
        admin_service,
        "record_action",
        lambda db, **kwargs: actions.append(kwargs),
    )

    response = client.post(
        "/api/admin/users",
        json={
            "email": "  NEW.USER@example.com ",
            "full_name": "  New User ",
            "organization": "  Registry  ",
            "role": "verifier",
            "initial_password": "a-long-initial-password",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["email"] == "new.user@example.com"
    assert created["full_name"] == "New User"
    assert created["organization"] == "Registry"
    assert created["role"] == "verifier"
    assert "password" not in created
    assert "password_hash" not in created
    user = db.get(User, created["id"])
    assert user is not None
    assert verify_password("a-long-initial-password", user.password_hash)
    assert actions == [
        {
            "actor": admin,
            "action": "user.created",
            "entity": "user",
            "entity_id": user.id,
            "payload": {"email": "new.user@example.com", "role": "verifier"},
        }
    ]


def test_create_user_rejects_invalid_or_duplicate_email(client, login, make_user):
    login(Role.ADMIN)

    invalid = client.post(
        "/api/admin/users",
        json={
            "email": "not-an-email",
            "full_name": "New User",
            "role": "buyer",
            "initial_password": "a-long-initial-password",
        },
    )
    assert invalid.status_code == 422

    too_short = client.post(
        "/api/admin/users",
        json={
            "email": "new@example.com",
            "full_name": "New User",
            "role": "buyer",
            "initial_password": "short",
        },
    )
    assert too_short.status_code == 422

    too_long = client.post(
        "/api/admin/users",
        json={
            "email": "long@example.com",
            "full_name": "Long Password",
            "role": "buyer",
            "initial_password": "é" * 37,
        },
    )
    assert too_long.status_code == 422

    make_user(Role.BUYER, email="existing@example.com")
    duplicate = client.post(
        "/api/admin/users",
        json={
            "email": "EXISTING@example.com",
            "full_name": "Duplicate User",
            "role": "buyer",
            "initial_password": "a-long-initial-password",
        },
    )
    assert duplicate.status_code == 409


def test_admin_can_change_role_and_deactivate_user_with_audit(
    client, login, make_user, monkeypatch
):
    from app.auth import admin_service

    admin = login(Role.ADMIN)
    user = make_user(Role.DEVELOPER, email="dev@example.com")
    actions = []
    monkeypatch.setattr(
        admin_service,
        "record_action",
        lambda db, **kwargs: actions.append(kwargs),
    )

    response = client.patch(
        f"/api/admin/users/{user.id}",
        json={"role": "buyer", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "buyer"
    assert response.json()["is_active"] is False

    blocked_login = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "test-password"},
    )
    assert blocked_login.status_code == 401

    reactivated = client.patch(
        f"/api/admin/users/{user.id}",
        json={"is_active": True},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True
    assert [action["action"] for action in actions] == [
        "user.role_changed",
        "user.deactivated",
        "user.activated",
    ]
    assert all(action["actor"] == admin for action in actions)
    assert all(action["entity_id"] == user.id for action in actions)


def test_admin_cannot_change_own_role_or_deactivate_self(client, login):
    admin = login(Role.ADMIN)

    role_change = client.patch(
        f"/api/admin/users/{admin.id}",
        json={"role": "buyer"},
    )
    deactivate = client.patch(
        f"/api/admin/users/{admin.id}",
        json={"is_active": False},
    )

    assert role_change.status_code == 409
    assert deactivate.status_code == 409


def test_user_update_rejects_empty_patch_and_missing_user(client, login):
    login(Role.ADMIN)

    assert client.patch("/api/admin/users/1", json={}).status_code == 422
    assert client.patch("/api/admin/users/999999", json={"is_active": False}).status_code == 404
