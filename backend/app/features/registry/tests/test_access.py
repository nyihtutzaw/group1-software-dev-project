"""#30 — registry staff grant and revoke buyer access to projects."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.auth.models import Role
from app.features.audit.ledger import verify_ledger_chain
from app.features.audit.models import LedgerEntry
from app.features.registry.models import RegistryProjectAccess
from app.features.registry.schemas import PublicationIn
from app.features.registry.service import publish_credit
from tests.support import PASSWORD

URL = "/api/registry/access"


def sign_in(client, user):
    response = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.text


@pytest.fixture
def setup(db, make_user):
    developer = make_user(Role.DEVELOPER, email="owner@test.local")
    publisher = make_user(Role.REGISTRY_STAFF, email="publisher@test.local")
    credit = publish_credit(
        db,
        developer=developer,
        actor=publisher,
        data=PublicationIn(
            serial="CRVR-0147-2026-A00000001-000000001-000008400",
            project_reference="CRVR-0147",
            project_name="Nan Reforestation Phase II",
            country="Thailand",
            methodology="VM0047",
            vintage=2026,
            quantity=8400,
            verifier_name="TUV Nord",
            verification_reference="VER-1",
            approval_reference="APP-1",
            signed_off_at=datetime(2026, 1, 2, tzinfo=UTC),
            issued_at=datetime(2026, 2, 2, tzinfo=UTC),
        ),
    )
    buyer = make_user(Role.BUYER, email="grantee@test.local")
    return {"credit": credit, "buyer": buyer, "developer": developer}


@pytest.mark.parametrize("role", [Role.REGISTRY_STAFF, Role.ADMIN])
def test_staff_grant_and_revoke_apply_on_buyer_next_load(client, db, make_user, setup, role):
    staff = make_user(role, email=f"granting-{role.value}@test.local")
    buyer = setup["buyer"]
    sign_in(client, buyer)
    assert client.get("/api/registry/credits").json()["total"] == 0

    sign_in(client, staff)
    body = {"project_reference": "CRVR-0147", "buyer_id": buyer.id}
    created = client.post(URL, json=body)
    assert created.status_code == 201, created.text
    assert created.json() == {
        "project_reference": "CRVR-0147",
        "project_name": "Nan Reforestation Phase II",
        "buyer_id": buyer.id,
        "buyer_name": buyer.full_name,
        "buyer_email": buyer.email,
        "buyer_organization": None,
        "buyer_active": True,
    }
    assert client.get(URL).json() == [created.json()]

    sign_in(client, buyer)
    listed = client.get("/api/registry/credits").json()
    assert [item["id"] for item in listed["items"]] == [setup["credit"].id]
    assert client.get(f"/api/registry/credits/{setup['credit'].id}/evidence").status_code == 200

    sign_in(client, staff)
    assert client.delete(f"{URL}/CRVR-0147/{buyer.id}").status_code == 204
    assert client.get(URL).json() == []

    sign_in(client, buyer)
    assert client.get("/api/registry/credits").json()["total"] == 0
    assert client.get(f"/api/registry/credits/{setup['credit'].id}").status_code == 404

    entries = db.scalars(
        select(LedgerEntry)
        .where(LedgerEntry.action.startswith("registry_access."))
        .order_by(LedgerEntry.id)
    ).all()
    assert [(e.action, e.entity, e.entity_id, e.payload, e.actor_id) for e in entries] == [
        ("registry_access.granted", "user", buyer.id, {"project_reference": "CRVR-0147"}, staff.id),
        ("registry_access.revoked", "user", buyer.id, {"project_reference": "CRVR-0147"}, staff.id),
    ]
    assert verify_ledger_chain(db) == (True, None)


@pytest.mark.parametrize("role", [Role.DEVELOPER, Role.VERIFIER, Role.BUYER])
def test_other_roles_cannot_manage_access(client, db, login, setup, role):
    login(role)
    body = {"project_reference": "CRVR-0147", "buyer_id": setup["buyer"].id}
    assert client.get(URL).status_code == 403
    assert client.get(f"{URL}/options").status_code == 403
    assert client.post(URL, json=body).status_code == 403
    assert client.delete(f"{URL}/CRVR-0147/{setup['buyer'].id}").status_code == 403
    assert db.scalar(select(RegistryProjectAccess)) is None


def test_anonymous_cannot_manage_access(client, setup):
    body = {"project_reference": "CRVR-0147", "buyer_id": setup["buyer"].id}
    assert client.get(URL).status_code == 401
    assert client.get(f"{URL}/options").status_code == 401
    assert client.post(URL, json=body).status_code == 401
    assert client.delete(f"{URL}/CRVR-0147/{setup['buyer'].id}").status_code == 401


def test_options_list_active_buyers_and_published_projects(client, db, login, make_user, setup):
    inactive = make_user(Role.BUYER, email="inactive-buyer@test.local")
    inactive.is_active = False
    db.flush()
    login(Role.REGISTRY_STAFF)
    options = client.get(f"{URL}/options").json()
    assert [buyer["id"] for buyer in options["buyers"]] == [setup["buyer"].id]
    assert set(options["buyers"][0]) == {"id", "full_name", "email", "organization"}
    assert options["projects"] == [
        {"project_reference": "CRVR-0147", "project_name": "Nan Reforestation Phase II"}
    ]


def test_grant_validation(client, db, login, make_user, setup):
    login(Role.REGISTRY_STAFF)
    buyer = setup["buyer"]
    unknown = client.post(URL, json={"project_reference": "CRVR-9999", "buyer_id": buyer.id})
    assert unknown.status_code == 404
    developer = client.post(
        URL, json={"project_reference": "CRVR-0147", "buyer_id": setup["developer"].id}
    )
    assert developer.status_code == 422
    assert (
        client.post(URL, json={"project_reference": "CRVR-0147", "buyer_id": 999999}).status_code
        == 422
    )
    inactive = make_user(Role.BUYER, email="inactive@test.local")
    inactive.is_active = False
    db.flush()
    body = {"project_reference": "CRVR-0147", "buyer_id": inactive.id}
    assert client.post(URL, json=body).status_code == 422
    for bad in ({"project_reference": "", "buyer_id": buyer.id}, {"project_reference": "X"}):
        assert client.post(URL, json=bad).status_code == 422

    body = {"project_reference": "CRVR-0147", "buyer_id": buyer.id}
    assert client.post(URL, json=body).status_code == 201
    assert client.post(URL, json=body).status_code == 409
    assert len(client.get(URL).json()) == 1
    assert client.delete(f"{URL}/CRVR-0147/999999").status_code == 404
    assert client.delete(f"{URL}/CRVR-OTHER/{buyer.id}").status_code == 404
    granted = db.scalars(
        select(LedgerEntry.action).where(LedgerEntry.action.startswith("registry_access."))
    ).all()
    assert granted == ["registry_access.granted"]  # failed attempts write nothing


def test_inactive_staff_session_is_rejected(client, db, login, setup):
    staff = login(Role.REGISTRY_STAFF)
    staff.is_active = False
    db.flush()
    assert client.get(URL).status_code == 401
