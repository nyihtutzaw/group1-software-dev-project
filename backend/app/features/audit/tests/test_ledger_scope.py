"""Who reads which ledger entries: staff all, verifiers their assignments, buyers their grants."""

from datetime import UTC, date, datetime

import pytest

from app.auth.models import Role
from app.features.audit.ledger import record_action
from app.features.registry.models import RegistryProjectAccess
from app.features.registry.schemas import PublicationIn
from app.features.registry.service import publish_credit
from app.features.verification.models import VerificationAssignment
from tests.support import PASSWORD


def sign_in(client, user):
    response = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.text


def actions(client) -> list[str]:
    response = client.get("/api/ledger")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(body["items"])
    return sorted(entry["action"] for entry in body["items"])


@pytest.fixture
def ledger(db, make_user, make_project):
    """Two projects with entries, a credit of the first, two buyers, a verifier, admin actions."""
    developer = make_user(Role.DEVELOPER, email="dev@test.local")
    staff = make_user(Role.REGISTRY_STAFF, email="staff@test.local")
    verifier = make_user(Role.VERIFIER, email="verifier@test.local")
    buyer = make_user(Role.BUYER, email="buyer@test.local")
    other_buyer = make_user(Role.BUYER, email="other.buyer@test.local")
    granted = make_project(owner=developer)
    hidden = make_project(owner=developer)

    for project in (granted, hidden):
        record_action(
            db,
            actor=developer,
            action="evidence.sealed",
            entity="project",
            entity_id=project.id,
            payload={"kind": "land_title", "filename": "title-deed.pdf", "sha256": "a" * 64},
        )
    record_action(
        db,
        actor=staff,
        action="verification.approved",
        entity="project",
        entity_id=granted.id,
        payload={"report_id": 1, "rationale": "Owner phone 0812345678 confirmed"},
    )
    db.add(
        VerificationAssignment(
            project_id=granted.id,
            verifier_id=verifier.id,
            assigned_by_id=staff.id,
            due_date=date(2026, 12, 1),
        )
    )
    credit = publish_credit(
        db,
        developer=developer,
        actor=staff,
        data=PublicationIn(
            serial=f"{granted.code}-2026-A00000001-000000001-000000100",
            project_reference=granted.code,
            project_name=granted.name,
            country="Thailand",
            methodology="VM0047",
            vintage=2026,
            quantity=100,
            verifier_name="Test verifier",
            verification_reference="VER-1",
            approval_reference="APP-1",
            signed_off_at=datetime(2026, 1, 2, tzinfo=UTC),
            issued_at=datetime(2026, 2, 2, tzinfo=UTC),
        ),
    )
    for holder in (buyer, other_buyer):
        db.add(RegistryProjectAccess(project_reference=granted.code, buyer_id=holder.id))
        record_action(
            db,
            actor=staff,
            action="registry_access.granted",
            entity="user",
            entity_id=holder.id,
            payload={"project_reference": granted.code},
        )
        record_action(
            db,
            actor=staff,
            action="credit.allocated",
            entity="credit",
            entity_id=credit.id,
            payload={"credit_id": credit.id, "buyer_id": holder.id, "quantity": 10},
        )
    record_action(
        db,
        actor=staff,
        action="user.created",
        entity="user",
        entity_id=buyer.id,
        payload={"email": buyer.email, "role": "buyer"},
    )
    db.flush()
    return {"staff": staff, "verifier": verifier, "buyer": buyer, "developer": developer}


def test_staff_read_every_entry(client, ledger):
    sign_in(client, ledger["staff"])
    assert len(actions(client)) == 8


def test_verifier_reads_only_assigned_projects(client, ledger):
    sign_in(client, ledger["verifier"])
    assert actions(client) == ["evidence.sealed", "verification.approved"]


def test_unassigned_verifier_reads_nothing(client, ledger, make_user):
    sign_in(client, make_user(Role.VERIFIER, email="unassigned@test.local"))
    assert actions(client) == []


def test_buyer_reads_granted_project_without_identities_or_private_fields(client, ledger):
    sign_in(client, ledger["buyer"])
    items = client.get("/api/ledger").json()["items"]

    assert sorted(entry["action"] for entry in items) == [
        "credit.allocated",  # their own allocation only
        "evidence.sealed",  # the granted project only
        "registry_access.granted",  # their own grant only
        "verification.approved",
    ]
    for entry in items:
        assert entry["actor_id"] is None
        assert entry["actor_email"] is None
        assert entry["actor_role"]  # the role stays, so the trail still says who acted
    by_action = {entry["action"]: entry["payload"] for entry in items}
    assert by_action["evidence.sealed"] == {"kind": "land_title", "sha256": "a" * 64}
    assert by_action["verification.approved"] == {}
    assert by_action["credit.allocated"] == {"quantity": 10}
    text = str(items)
    assert "title-deed.pdf" not in text
    assert "0812345678" not in text
    assert "@test.local" not in text


def test_buyer_without_grants_reads_nothing_but_can_check_the_chain(client, ledger, make_user):
    sign_in(client, make_user(Role.BUYER, email="new.buyer@test.local"))
    assert actions(client) == []
    assert client.get("/api/ledger/verify").json() == {"valid": True, "error": None}
