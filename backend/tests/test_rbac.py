import pytest

from app.auth.models import Role


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (Role.VERIFIER, 200),
        (Role.REGISTRY_STAFF, 200),
        (Role.ADMIN, 200),
        (Role.DEVELOPER, 403),
        (Role.BUYER, 403),
    ],
)
def test_verification_queue_is_limited_to_reviewing_roles(client, login, role, expected):
    login(role)

    assert client.get("/api/verifications/queue").status_code == expected


def test_protected_route_requires_sign_in(client):
    assert client.get("/api/projects").status_code == 401


def test_public_registry_needs_no_sign_in(client):
    assert client.get("/api/registry/credits").status_code == 200
