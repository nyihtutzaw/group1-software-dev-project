from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select, update

from app.auth.models import Role
from app.features.registry.models import (
    RegistryCredit,
    RegistryCreditEvent,
    RegistryEvidence,
    RegistryProjectAccess,
)
from app.features.registry.schemas import PublicationIn
from app.features.registry.service import change_status, publish_credit


@pytest.fixture
def publication(db, make_user):
    developer = make_user(Role.DEVELOPER)
    staff = make_user(Role.REGISTRY_STAFF)

    def create(serial="TH-0147-2026-A-00001-08400", project="CRVR-0147", **overrides):
        fields = dict(
            serial=serial,
            project_reference=project,
            project_name="Nan Reforestation Phase II",
            country="Thailand",
            methodology="Afforestation and reforestation",
            vintage=2026,
            quantity=8400,
            verifier_name="TUV Nord (VVB-114)",
            verification_reference="VER-0147",
            approval_reference="APP-0147",
            signed_off_at=datetime(2026, 1, 2, tzinfo=UTC),
            issued_at=datetime(2026, 2, 2, tzinfo=UTC),
        )
        fields.update(overrides)
        return publish_credit(db, data=PublicationIn(**fields), developer=developer, actor=staff)

    create.developer = developer
    create.staff = staff
    return create


def test_public_search_and_safe_detail(client, publication):
    credit = publication()
    for term in ("nan", "0147-2026", "THAILAND", "CRVR-0147", "  Thailand "):
        response = client.get("/api/registry/credits", params={"q": term})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["id"] == credit.id
    detail = client.get(f"/api/registry/credits/{credit.id}").json()
    assert detail["history"][0]["action"] == "issued"
    assert detail["monitoring"] == detail["ledger_status"] == "not_available"
    assert set(detail).isdisjoint({"developer_id", "published_by_id", "snapshot_sha256"})
    assert client.get("/api/registry/credits", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/registry/credits", params={"q": "_"}).json()["total"] == 0
    assert client.get("/api/registry/credits", params={"q": "missing"}).json()["total"] == 0


def test_pagination_and_validation(client, publication):
    older = publication(vintage=2025)
    newer = publication(serial="TH-OTHER", vintage=2026)
    first = client.get("/api/registry/credits?page_size=1").json()
    assert first["total"] == 2
    assert first["items"][0]["id"] == newer.id
    assert (
        client.get("/api/registry/credits?page_size=1&page=2").json()["items"][0]["id"] == older.id
    )
    assert client.get("/api/registry/credits?page=5").json()["items"] == []
    for query in ("page=0", "page_size=101", "page_size=0", "q=" + "x" * 201):
        assert client.get("/api/registry/credits?" + query).status_code == 422


def test_buyer_grants_enforced_on_every_endpoint(client, db, login, publication):
    allowed = publication()
    denied = publication(serial="PRIVATE-SERIAL", project="PRIVATE-PROJECT")
    buyer = login(Role.BUYER)
    assert client.get("/api/registry/credits").json()["total"] == 0
    db.add(RegistryProjectAccess(project_reference=allowed.project_reference, buyer_id=buyer.id))
    db.flush()
    response = client.get("/api/registry/credits").json()
    assert [item["id"] for item in response["items"]] == [allowed.id]
    assert client.get(f"/api/registry/credits/{allowed.id}").status_code == 200
    for suffix in ("", "/evidence", "/integrity"):
        assert client.get(f"/api/registry/credits/{denied.id}{suffix}").status_code == 404
        assert client.get(f"/api/registry/credits/999999{suffix}").status_code == 404


def test_evidence_is_allowlisted_and_excludes_sources(client, db, login, publication):
    credit = publication()
    buyer = login(Role.BUYER)
    db.add(RegistryProjectAccess(project_reference=credit.project_reference, buyer_id=buyer.id))
    db.add_all(
        [
            RegistryEvidence(
                credit_id=credit.id,
                title="Reviewed report",
                summary="Approved summary",
                source_reference="private/storage/report.pdf",
                buyer_visible=True,
            ),
            RegistryEvidence(
                credit_id=credit.id,
                title="Private owner",
                summary="Private phone number",
                source_reference="private/raw.pdf",
            ),
        ]
    )
    db.flush()
    response = client.get(f"/api/registry/credits/{credit.id}/evidence")
    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "id": response.json()["items"][0]["id"],
            "title": "Reviewed report",
            "summary": "Approved summary",
        }
    ]
    for value in ("source_reference", "private/", "Private owner", "Private phone", "developer_id"):
        assert value not in response.text
    # Public detail never embeds even the approved evidence summaries.
    client.post("/api/auth/logout")
    assert "Approved summary" not in client.get(f"/api/registry/credits/{credit.id}").text
    assert client.get(f"/api/registry/credits/{credit.id}/evidence").status_code == 401


@pytest.mark.parametrize("role", [Role.DEVELOPER, Role.VERIFIER])
def test_non_buyer_roles_cannot_read_evidence(client, login, publication, role):
    credit = publication()
    if role == Role.DEVELOPER:
        # This developer already exists in the publication fixture.
        client.post(
            "/api/auth/login", json={"email": "developer@test.local", "password": "test-password"}
        )
    else:
        login(role)
    assert client.get(f"/api/registry/credits/{credit.id}/evidence").status_code == 403


@pytest.mark.parametrize("role", [Role.REGISTRY_STAFF, Role.ADMIN])
def test_staff_can_read_safe_empty_pack(client, login, publication, role):
    credit = publication()
    if role == Role.REGISTRY_STAFF:
        client.post(
            "/api/auth/login",
            json={"email": "registry_staff@test.local", "password": "test-password"},
        )
    else:
        login(role)
    assert client.get(f"/api/registry/credits/{credit.id}/evidence").json()["items"] == []


def test_bad_session_cannot_fall_back_to_public_access(client, publication):
    publication()
    client.cookies.set("crvr_session", "invalid")
    assert client.get("/api/registry/credits").status_code == 401


def test_inactive_buyer_cannot_use_old_session(client, db, login, publication):
    publication()
    user = login(Role.BUYER)
    user.is_active = False
    db.flush()
    assert client.get("/api/registry/credits").status_code == 401


def test_integrity_detects_changes_without_claiming_ledger_authenticity(client, db, publication):
    credit = publication()
    url = f"/api/registry/credits/{credit.id}/integrity"
    response = client.get(url).json()
    assert response["snapshot_matches"] is True
    assert response["ledger_status"] == "not_available"
    credit.quantity = 1
    db.flush()
    assert client.get(url).json()["snapshot_matches"] is False


def test_lifecycle_records_history_and_prevents_reuse(client, db, publication):
    credit = publication()
    change_status(db, credit.id, status="retired", actor=publication.staff)
    detail = client.get(f"/api/registry/credits/{credit.id}").json()
    assert detail["status"] == "retired"
    assert [item["action"] for item in detail["history"]] == ["issued", "retired"]
    # Terminal credits remain discoverable for transparency.
    assert client.get("/api/registry/credits").json()["total"] == 1
    with pytest.raises(HTTPException) as error:
        change_status(db, credit.id, status="revoked", actor=publication.staff)
    assert error.value.status_code == 409
    assert client.get(f"/api/registry/credits/{credit.id}/integrity").json()["snapshot_matches"]


def test_duplicate_serial_is_atomic(db, publication):
    publication()
    with pytest.raises(HTTPException) as error:
        publication()
    assert error.value.status_code == 409
    assert len(db.scalars(select(RegistryCredit)).all()) == 1
    assert len(db.scalars(select(RegistryCreditEvent)).all()) == 1


def test_only_staff_can_publish_or_change_status(db, publication, make_user):
    credit = publication()
    buyer = make_user(Role.BUYER)
    data = PublicationIn.model_validate(credit, from_attributes=True)
    with pytest.raises(HTTPException) as error:
        publish_credit(db, data=data, developer=publication.developer, actor=buyer)
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        change_status(db, credit.id, status="retired", actor=buyer)
    assert error.value.status_code == 403


def test_independent_developer_required(db, publication):
    credit = publication()
    data = PublicationIn.model_validate(credit, from_attributes=True)
    with pytest.raises(HTTPException) as error:
        publish_credit(db, data=data, developer=publication.staff, actor=publication.staff)
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    "changes",
    [
        {"signed_off_at": datetime(2026, 3, 2, tzinfo=UTC)},
        {"issued_at": datetime.now(UTC) + timedelta(days=1)},
        {"signed_off_at": datetime(2026, 1, 2)},
    ],
)
def test_invalid_publication_dates_rejected(publication, changes):
    with pytest.raises(HTTPException) as error:
        publication(**changes)
    assert error.value.status_code == 422


def test_demo_seed_is_idempotent_and_requires_development(db, make_user, monkeypatch):
    from app.core.config import get_settings
    from app.features.registry.demo import seed_registry_demo

    for role, email in (
        (Role.DEVELOPER, "developer"),
        (Role.REGISTRY_STAFF, "staff"),
        (Role.BUYER, "buyer"),
    ):
        make_user(role, email=f"{email}@crvr.local")
    seed_registry_demo(db)
    seed_registry_demo(db)
    assert len(db.scalars(select(RegistryCredit)).all()) == 3
    assert len(db.scalars(select(RegistryProjectAccess)).all()) == 2
    assert len(db.scalars(select(RegistryCreditEvent)).all()) == 4
    monkeypatch.setattr(get_settings(), "app_env", "production")
    with pytest.raises(RuntimeError, match="only in development"):
        seed_registry_demo(db)


def test_status_transition_refreshes_previously_loaded_credit(db, publication):
    credit = publication()
    # Simulate a status changed after this session first loaded the credit.
    db.execute(
        update(RegistryCredit)
        .where(RegistryCredit.id == credit.id)
        .values(status="retired")
        .execution_options(synchronize_session=False)
    )
    assert credit.status == "active"
    with pytest.raises(HTTPException) as error:
        change_status(db, credit.id, status="revoked", actor=publication.staff)
    assert error.value.status_code == 409
    assert credit.status == "retired"
