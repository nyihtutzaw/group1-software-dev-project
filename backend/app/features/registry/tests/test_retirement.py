"""#44 — staff allocate credit ranges to buyers; buyers retire them permanently."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.auth.models import Role
from app.features.audit.ledger import verify_ledger_chain
from app.features.audit.models import LedgerEntry
from app.features.registry.holdings import serial_block
from app.features.registry.models import RegistryHolding, RegistryProjectAccess
from app.features.registry.schemas import PublicationIn
from app.features.registry.service import change_status, publish_credit
from tests.support import PASSWORD

SERIAL = "CRVR-0147-2026-A00000001-000000001-000000100"
PREFIX = "CRVR-0147-2026-A00000001"
YEAR = datetime.now(UTC).year
RETIRE = {"beneficiary": "Nordic Airways", "reason": "2026 Scope 1 offset", "reporting_year": YEAR}


def sign_in(client, user):
    response = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.text


@pytest.fixture
def batch(db, make_user):
    developer = make_user(Role.DEVELOPER, email="owner@test.local")
    staff = make_user(Role.REGISTRY_STAFF, email="registrar@test.local")
    credit = publish_credit(
        db,
        developer=developer,
        actor=staff,
        data=PublicationIn(
            serial=SERIAL,
            project_reference="CRVR-0147",
            project_name="Nan Reforestation Phase II",
            country="Thailand",
            methodology="VM0047",
            vintage=2026,
            quantity=100,
            verifier_name="TUV Nord",
            verification_reference="VER-1",
            approval_reference="APP-1",
            signed_off_at=datetime(2026, 1, 2, tzinfo=UTC),
            issued_at=datetime(2026, 2, 2, tzinfo=UTC),
        ),
    )
    buyer = make_user(Role.BUYER, email="holder@test.local")
    other = make_user(Role.BUYER, email="other-buyer@test.local")
    for user in (buyer, other):
        db.add(RegistryProjectAccess(project_reference="CRVR-0147", buyer_id=user.id))
    db.flush()
    return {"credit": credit, "staff": staff, "buyer": buyer, "other": other}


def allocate(client, batch, quantity, email="holder@test.local"):
    sign_in(client, batch["staff"])
    return client.post(
        f"/api/registry/credits/{batch['credit'].id}/holdings",
        json={"buyer_email": email, "quantity": quantity},
    )


def retire(client, user, holding_id, quantity, **changes):
    sign_in(client, user)
    return client.post(
        f"/api/registry/holdings/{holding_id}/retire",
        json={"quantity": quantity, **RETIRE, **changes},
    )


def ledger(db, action):
    return db.scalars(select(LedgerEntry).where(LedgerEntry.action == action)).all()


def test_serial_block_keeps_the_batch_serial_format(batch):
    credit = batch["credit"]
    assert serial_block(credit, 1, 40) == f"{PREFIX}-000000001-000000040"
    credit.serial = "TH-0147-2026-A-00001-08400"
    assert serial_block(credit, 12, 500) == "TH-0147-2026-A-00012-00500"
    credit.serial = "NO-RANGE"
    assert serial_block(credit, 1, 2) == "NO-RANGE #1–2"


def test_staff_allocate_ranges_and_each_buyer_sees_only_their_own(client, db, batch):
    first = allocate(client, batch, 40)
    assert first.status_code == 201, first.text
    assert first.json()["serial_block"] == f"{PREFIX}-000000001-000000040"
    assert first.json()["buyer_email"] == "holder@test.local"
    second = allocate(client, batch, 10, email="Other-Buyer@test.local")
    assert second.json()["first_unit"] == 41
    assert second.json()["last_unit"] == 50

    staff_view = client.get(f"/api/registry/credits/{batch['credit'].id}/holdings").json()
    assert (staff_view["allocated"], staff_view["unallocated"], staff_view["retired"]) == (
        50,
        50,
        0,
    )
    assert [item["buyer_email"] for item in staff_view["items"]] == [
        "holder@test.local",
        "other-buyer@test.local",
    ]

    sign_in(client, batch["buyer"])
    own = client.get(f"/api/registry/credits/{batch['credit'].id}/holdings").json()
    assert [(item["first_unit"], item["buyer_email"]) for item in own["items"]] == [(1, None)]

    entries = ledger(db, "credit.allocated")
    assert [(e.entity, e.entity_id, e.payload["quantity"]) for e in entries] == [
        ("credit", batch["credit"].id, 40),
        ("credit", batch["credit"].id, 10),
    ]


def test_partial_retirement_splits_the_range_and_is_public(client, db, batch):
    holding = allocate(client, batch, 40).json()
    result = retire(client, batch["buyer"], holding["id"], 15)
    assert result.status_code == 200, result.text
    retired, remaining = result.json()["retired"], result.json()["remaining"]
    assert (retired["first_unit"], retired["last_unit"], retired["status"]) == (1, 15, "retired")
    assert retired["serial_block"] == f"{PREFIX}-000000001-000000015"
    assert (remaining["first_unit"], remaining["last_unit"], remaining["status"]) == (
        16,
        40,
        "held",
    )

    client.post("/api/auth/logout")
    public = client.get(f"/api/registry/credits/{batch['credit'].id}/retirements").json()
    assert public == {
        "quantity": 100,
        "retired_quantity": 15,
        "items": [
            {
                "serial_block": f"{PREFIX}-000000001-000000015",
                "quantity": 15,
                **RETIRE,
                "retired_at": public["items"][0]["retired_at"],
            }
        ],
    }
    assert "holder@test.local" not in str(public)
    detail = client.get(f"/api/registry/credits/{batch['credit'].id}").json()
    assert detail["status"] == "active"

    [entry] = ledger(db, "credit.retired")
    assert entry.actor_id == batch["buyer"].id
    assert entry.payload["first_unit"] == 1 and entry.payload["last_unit"] == 15
    assert entry.payload["beneficiary"] == "Nordic Airways"
    assert verify_ledger_chain(db) == (True, None)


def test_retired_credits_are_permanently_locked(client, db, batch):
    holding = allocate(client, batch, 40).json()
    retire(client, batch["buyer"], holding["id"], 40)
    again = retire(client, batch["buyer"], holding["id"], 1)
    assert again.status_code == 409

    for sql in (
        "UPDATE registry_holdings SET status = 'held', retired_at = NULL, beneficiary = NULL,"
        " reason = NULL, reporting_year = NULL WHERE id = :id",
        "UPDATE registry_holdings SET buyer_id = :other WHERE id = :id",
        "DELETE FROM registry_holdings WHERE id = :id",
    ):
        with pytest.raises(DBAPIError, match="permanently locked"), db.begin_nested():
            db.execute(text(sql), {"id": holding["id"], "other": batch["other"].id})
    db.expire_all()
    assert db.get(RegistryHolding, holding["id"]).status == "retired"


def test_retiring_every_unit_retires_the_batch(client, db, batch):
    first = allocate(client, batch, 60).json()
    second = allocate(client, batch, 40, email="other-buyer@test.local").json()
    retire(client, batch["buyer"], first["id"], 60)
    detail = client.get(f"/api/registry/credits/{batch['credit'].id}").json()
    assert detail["status"] == "active"
    assert retire(client, batch["other"], second["id"], 40).status_code == 200
    detail = client.get(f"/api/registry/credits/{batch['credit'].id}").json()
    assert detail["status"] == "retired"
    assert [event["action"] for event in detail["history"]] == ["issued", "retired"]
    public = client.get(f"/api/registry/credits/{batch['credit'].id}/retirements").json()
    assert public["retired_quantity"] == 100


def test_allocation_rules(client, db, login, make_user, batch):
    url = f"/api/registry/credits/{batch['credit'].id}/holdings"
    body = {"buyer_email": "holder@test.local", "quantity": 1}
    for role in (Role.DEVELOPER, Role.VERIFIER, Role.BUYER):
        login(role)
        assert client.post(url, json=body).status_code == 403
    client.post("/api/auth/logout")
    assert client.post(url, json=body).status_code == 401

    no_grant = make_user(Role.BUYER, email="no-grant@test.local")
    assert no_grant.id
    assert allocate(client, batch, 1, email="no-grant@test.local").status_code == 409
    assert allocate(client, batch, 1, email="owner@test.local").status_code == 422
    assert allocate(client, batch, 1, email="nobody@test.local").status_code == 422
    assert allocate(client, batch, 0).status_code == 422
    assert allocate(client, batch, 101).status_code == 422
    assert allocate(client, batch, 100).status_code == 201
    over = allocate(client, batch, 1)
    assert over.status_code == 422
    assert "Only 0 unallocated" in over.json()["detail"]
    assert len(ledger(db, "credit.allocated")) == 1


def test_revoked_batch_cannot_be_allocated_or_retired(client, db, batch):
    holding = allocate(client, batch, 10).json()
    change_status(db, batch["credit"].id, status="revoked", actor=batch["staff"])
    assert allocate(client, batch, 1).status_code == 409
    assert retire(client, batch["buyer"], holding["id"], 1).status_code == 409


def test_retirement_rules(client, db, login, batch):
    holding = allocate(client, batch, 10).json()
    # Only the holder can retire; another buyer cannot even see the holding exists.
    assert retire(client, batch["other"], holding["id"], 1).status_code == 404
    assert retire(client, batch["buyer"], 999999, 1).status_code == 404
    sign_in(client, batch["staff"])
    response = client.post(
        f"/api/registry/holdings/{holding['id']}/retire", json={"quantity": 1, **RETIRE}
    )
    assert response.status_code == 403
    assert retire(client, batch["buyer"], holding["id"], 11).status_code == 422
    assert retire(client, batch["buyer"], holding["id"], 0).status_code == 422
    assert (
        retire(client, batch["buyer"], holding["id"], 1, reporting_year=YEAR + 1).status_code == 422
    )
    for field in ("beneficiary", "reason"):
        assert retire(client, batch["buyer"], holding["id"], 1, **{field: "  "}).status_code == 422
    assert ledger(db, "credit.retired") == []
    assert db.get(RegistryHolding, holding["id"]).status == "held"


def test_holdings_require_sign_in_and_grants(client, db, login, batch):
    url = f"/api/registry/credits/{batch['credit'].id}/holdings"
    assert client.get(url).status_code == 401
    login(Role.DEVELOPER)
    assert client.get(url).status_code == 403
    buyer = login(Role.BUYER)  # signed in, but no grant for this project
    assert buyer.id
    assert client.get(url).status_code == 404
    assert client.get(f"/api/registry/credits/{batch['credit'].id}/retirements").status_code == 404
