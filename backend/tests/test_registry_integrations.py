"""Real F1 → F3 approval → issuance → F4 reads, including privacy and atomicity."""

import hashlib
import json
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select, text

from app.auth.models import Role
from app.core.config import get_settings
from app.features.audit.ledger import record_action, verify_ledger_chain
from app.features.audit.models import LedgerEntry
from app.features.boundary.models import BoundarySource, FlagStatus, OverlapFlag
from app.features.boundary.service import save_boundary
from app.features.registration.models import Project, ProjectStatus
from app.features.registration.service import buyer_evidence_summaries
from app.features.registry.models import RegistryCredit, RegistryCreditEvent, RegistryProjectAccess
from app.features.registry.service import snapshot_digest
from app.features.verification.models import CHECKLIST
from tests.conftest import PASSWORD
from tests.geo import BASE, square

ISSUE = {"country": "Thailand", "vintage": datetime.now(UTC).year, "quantity": 73}
PRIVATE = "CONFIDENTIAL-OWNER-PHONE-1234"


def sign_in(client, user):
    response = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.text


@pytest.fixture
def workflow(client, db, make_user, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_dir", str(tmp_path))
    developer = make_user(Role.DEVELOPER)
    developer.full_name = PRIVATE
    developer.organization = PRIVATE + "-ORG"
    staff = make_user(Role.REGISTRY_STAFF)
    verifier = make_user(Role.VERIFIER)
    buyer = make_user(Role.BUYER)
    sign_in(client, developer)
    body = {
        "name": "Real registry integration project",
        "methodology": "VM0047",
        "crediting_start_year": ISSUE["vintage"],
        "crediting_end_year": ISSUE["vintage"] + 20,
        "area_ha": 100,
        "est_removal_tco2e": 500,
        "baseline_summary": PRIVATE,
        "additionality_reasoning": PRIVATE * 5,
    }
    response = client.post("/api/projects", json=body)
    assert response.status_code == 201, response.text
    project = db.get(Project, response.json()["id"])
    hashes = []
    for kind in ("land_title", "additionality_proof"):
        content = f"%PDF-1.4 {kind} {PRIVATE}".encode()
        hashes.append(hashlib.sha256(content).hexdigest())
        upload = client.post(
            f"/api/projects/{project.id}/evidence",
            files={"file": (f"{PRIVATE}-{kind}.pdf", content, "application/pdf")},
            data={"kind": kind},
        )
        assert upload.status_code == 201, upload.text
    save_boundary(db, project, square(BASE[0] + 1, BASE[1]), BoundarySource.DRAWN, developer)
    response = client.post(f"/api/projects/{project.id}/submit")
    assert response.status_code == 200, response.text
    sign_in(client, staff)
    assigned = client.post(
        "/api/verifications/assignments",
        json={
            "project_id": project.id,
            "verifier_id": verifier.id,
            "due_date": date.today().isoformat(),
        },
    )
    assert assigned.status_code == 201, assigned.text
    sign_in(client, verifier)
    report = client.post(
        f"/api/verifications/assignments/{assigned.json()['id']}/report",
        json={
            "decision": "sign_off",
            "note": PRIVATE,
            "checklist": {key: True for key, _label in CHECKLIST},
            "risk_rating": "low",
        },
    )
    assert report.status_code == 200, report.text
    sign_in(client, staff)
    approved = client.post(
        f"/api/verifications/reports/{report.json()['report_id']}/decision",
        json={"decision": "approved", "rationale": PRIVATE},
    )
    assert approved.status_code == 200, approved.text
    db.refresh(project)
    assert project.status == ProjectStatus.VERIFIED
    return {
        "project": project,
        "staff": staff,
        "verifier": verifier,
        "developer": developer,
        "buyer": buyer,
        "hashes": hashes,
        "approval_id": approved.json()["approval"]["id"],
    }


def issue(client, workflow):
    sign_in(client, workflow["staff"])
    response = client.post(
        f"/api/verifications/projects/{workflow['project'].id}/issue", json=ISSUE
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_approve_issue_and_read_real_credit_in_registry(client, db, workflow):
    assert client.get("/api/registry/credits").json()["total"] == 0  # approved is not issued
    credit = issue(client, workflow)
    db.refresh(workflow["project"])
    assert workflow["project"].status == ProjectStatus.ISSUED
    # Low risk keeps 10% (7 of 73, half-up) in the buffer. The response is the tradable batch.
    assert credit["status"] == "active"
    assert credit["quantity"] == 66
    assert credit["quantity"] != workflow["project"].est_removal_tco2e
    rows = db.scalars(select(RegistryCredit).order_by(RegistryCredit.id)).all()
    assert [(row.status, row.quantity) for row in rows] == [("active", 66), ("buffer", 7)]
    assert sum(row.quantity for row in rows) == ISSUE["quantity"]
    assert all(row.source_project_id == workflow["project"].id for row in rows)
    assert all(row.source_approval_id == workflow["approval_id"] for row in rows)
    assert not rows[0].is_demo
    client.post("/api/auth/logout")
    results = client.get("/api/registry/credits", params={"q": workflow["project"].code}).json()
    assert [item["status"] for item in results["items"]] == ["active"]  # buffer: not a 2nd row
    assert results["items"][0] == credit
    every = client.get(
        "/api/registry/credits", params={"q": workflow["project"].code, "include_buffer": True}
    ).json()
    assert sorted(item["status"] for item in every["items"]) == ["active", "buffer"]
    detail = client.get(f"/api/registry/credits/{credit['id']}").json()
    assert detail["history"][0]["action"] == "issued"
    assert detail["buffer_quantity"] == 7
    assert client.get(f"/api/registry/credits/{credit['id']}/integrity").json()["snapshot_matches"]
    buffer = next(row for row in rows if row.status == "buffer")
    assert (
        client.get(f"/api/registry/credits/{buffer.id}/integrity").json()["ledger_status"]
        == "intact"
    )
    entries = db.scalars(
        select(LedgerEntry).where(LedgerEntry.action == "credit.issued").order_by(LedgerEntry.id)
    ).all()
    assert [entry.payload["quantity"] for entry in entries] == [66, 7]
    assert entries[0].payload["serial"] == credit["serial"]
    assert verify_ledger_chain(db) == (True, None)
    duplicate = (
        sign_in(client, workflow["staff"]),
        client.post(f"/api/verifications/projects/{workflow['project'].id}/issue", json=ISSUE),
    )[1]
    assert duplicate.status_code == 409
    assert db.scalar(select(func.count()).select_from(RegistryCredit)) == 2
    assert db.scalar(select(func.count()).select_from(RegistryCreditEvent)) == 2
    sign_in(client, workflow["staff"])
    blocked = client.post(
        f"/api/registry/credits/{buffer.id}/holdings",
        json={"buyer_email": workflow["buyer"].email, "quantity": 1},
    )
    assert blocked.status_code == 409
    assert "Buffer" in blocked.json()["detail"]


def tamper(db, sql, params):
    """Simulate direct database tampering by bypassing the ledger's write-once trigger."""
    db.execute(text("ALTER TABLE ledger_entries DISABLE TRIGGER ledger_entries_no_update_delete"))
    db.execute(text(sql), params)
    db.execute(text("ALTER TABLE ledger_entries ENABLE TRIGGER ledger_entries_no_update_delete"))
    db.expire_all()


def test_authenticity_checks_real_issuance_against_ledger(client, db, workflow):
    credit = issue(client, workflow)
    client.post("/api/auth/logout")
    entry = db.scalar(select(LedgerEntry).where(LedgerEntry.action == "credit.issued"))
    response = client.get(f"/api/registry/credits/{credit['id']}/integrity")
    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_matches"] is True
    assert body["ledger_status"] == "intact"
    assert [(item["id"], item["action"], item["hash"]) for item in body["entries"]] == [
        (entry.id, "credit.issued", entry.hash)
    ]
    # Public pointers only: no payload, actor or chain internals.
    assert set(body["entries"][0]) == {"id", "action", "created_at", "hash"}


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ledger_entries SET payload = CAST(:value AS json) WHERE id = :id",
        "UPDATE ledger_entries SET prev_hash = :value WHERE id = :id",
    ],
)
def test_authenticity_fails_when_ledger_entry_is_tampered(client, db, workflow, sql):
    credit = issue(client, workflow)
    entry = db.scalar(select(LedgerEntry).where(LedgerEntry.action == "credit.issued"))
    value = json.dumps({"credit_id": credit["id"], "serial": "FORGED", "quantity": 999999})
    if "prev_hash" in sql:
        value = "f" * 64
    tamper(db, sql, {"value": value, "id": entry.id})
    body = client.get(f"/api/registry/credits/{credit['id']}/integrity").json()
    assert body["ledger_status"] == "broken"
    assert "broken" in body["notice"]


def test_authenticity_fails_when_an_earlier_entry_is_tampered(client, db, workflow):
    first = db.scalar(select(LedgerEntry).order_by(LedgerEntry.id).limit(1))
    credit = issue(client, workflow)
    tamper(
        db,
        "UPDATE ledger_entries SET action = 'project.deleted' WHERE id = :id",
        {"id": first.id},
    )
    body = client.get(f"/api/registry/credits/{credit['id']}/integrity").json()
    assert body["ledger_status"] == "broken"


def test_authenticity_fails_when_published_batch_differs_from_sealed_issuance(client, db, workflow):
    credit = issue(client, workflow)
    row = db.get(RegistryCredit, credit["id"])
    row.quantity = 1_000_000
    row.snapshot_sha256 = snapshot_digest(row)  # a forger can recompute the digest...
    db.flush()
    body = client.get(f"/api/registry/credits/{credit['id']}/integrity").json()
    assert body["snapshot_matches"] is True
    assert body["ledger_status"] == "broken"  # ...but not the sealed ledger entry.


def test_authenticity_ignores_other_credits_entries(client, db, workflow):
    credit = issue(client, workflow)
    record_action(
        db,
        actor=workflow["staff"],
        action="credit.issued",
        entity="project",
        entity_id=999,
        payload={"credit_id": credit["id"] + 1, "serial": "OTHER"},
    )
    record_action(
        db,
        actor=workflow["staff"],
        action="project.created",
        entity="project",
        entity_id=999,
        payload={"credit_id": "not-a-number"},
    )
    body = client.get(f"/api/registry/credits/{credit['id']}/integrity").json()
    assert body["ledger_status"] == "intact"
    assert [item["action"] for item in body["entries"]] == ["credit.issued"]


def test_f1_safe_summary_contract_and_f4_pack_never_expose_sensitive_fields(client, db, workflow):
    credit = issue(client, workflow)
    safe = [
        item.model_dump(mode="json")
        for item in buyer_evidence_summaries(db, workflow["project"].id)
    ]
    assert len(safe) == 2
    assert all(set(item) == {"kind", "sealed_at", "sha256"} for item in safe)
    assert {item["sha256"] for item in safe} == set(workflow["hashes"])
    sign_in(client, workflow["buyer"])
    url = f"/api/registry/credits/{credit['id']}"
    assert client.get(url + "/evidence").status_code == 404
    db.add(
        RegistryProjectAccess(
            project_reference=workflow["project"].code, buyer_id=workflow["buyer"].id
        )
    )
    db.flush()
    response = client.get(url + "/evidence")
    assert response.status_code == 200
    assert response.json()["items"] == safe
    responses = [response, client.get(url), client.get("/api/registry/credits")]
    for response in responses:
        assert PRIVATE not in response.text
        for field in (
            "owner_id",
            "owner_name",
            "uploaded_by_id",
            "filename",
            "storage_key",
            "source_reference",
            "source_project_id",
            "source_approval_id",
            "rationale",
            "additionality_reasoning",
            "baseline_summary",
            "password",
            "developer_id",
        ):
            assert f'"{field}"' not in response.text
    client.post("/api/auth/logout")
    assert client.get(url + "/evidence").status_code == 401
    assert PRIVATE not in client.get(url).text
    assert PRIVATE not in client.get("/api/registry/credits").text
    # No project detail/file access is opened for buyers by the safe metadata handoff.
    sign_in(client, workflow["buyer"])
    assert client.get(f"/api/projects/{workflow['project'].id}").status_code == 403


@pytest.mark.parametrize("role", ["developer", "verifier", "buyer"])
def test_nonstaff_cannot_issue(client, db, workflow, role):
    sign_in(client, workflow[role])
    assert (
        client.post(
            f"/api/verifications/projects/{workflow['project'].id}/issue", json=ISSUE
        ).status_code
        == 403
    )
    assert db.scalar(select(func.count()).select_from(RegistryCredit)) == 0


@pytest.mark.parametrize(
    "state", [ProjectStatus.DRAFT, ProjectStatus.SUBMITTED, ProjectStatus.ISSUED]
)
def test_only_approved_unissued_project_can_issue(client, db, workflow, state):
    workflow["project"].status = state
    db.flush()
    response = client.post(
        f"/api/verifications/projects/{workflow['project'].id}/issue", json=ISSUE
    )
    assert response.status_code == 409
    assert db.scalar(select(func.count()).select_from(RegistryCredit)) == 0


@pytest.mark.parametrize("flag_status", [FlagStatus.OPEN, FlagStatus.DISPUTED])
def test_real_f2_gate_blocks_issuance_after_approval(
    client, db, workflow, make_project, flag_status
):
    other = make_project()
    db.add(
        OverlapFlag(
            project_id=workflow["project"].id,
            other_project_id=other.id,
            overlap_m2=100,
            overlap_pct=1.0,
            status=flag_status,
        )
    )
    db.flush()
    response = client.post(
        f"/api/verifications/projects/{workflow['project'].id}/issue", json=ISSUE
    )
    assert response.status_code == 409
    assert "overlaps" in response.json()["detail"]
    assert db.scalar(select(func.count()).select_from(RegistryCredit)) == 0
    db.refresh(workflow["project"])
    assert workflow["project"].status == ProjectStatus.VERIFIED


def test_ledger_failure_rolls_back_publication_history_and_project_state(
    client, db, workflow, monkeypatch
):
    def fail(*args, **kwargs):
        raise RuntimeError("Ledger unavailable")

    monkeypatch.setattr("app.features.verification.issuance.record_action", fail)
    with pytest.raises(RuntimeError, match="Ledger unavailable"):
        client.post(f"/api/verifications/projects/{workflow['project'].id}/issue", json=ISSUE)
    assert db.scalar(select(func.count()).select_from(RegistryCredit)) == 0
    assert db.scalar(select(func.count()).select_from(RegistryCreditEvent)) == 0
    db.refresh(workflow["project"])
    assert workflow["project"].status == ProjectStatus.VERIFIED


@pytest.mark.parametrize(
    "changes",
    [{"quantity": 0}, {"quantity": 1.5}, {"country": " "}, {"vintage": 1899}, {"vintage": 2199}],
)
def test_invalid_batch_values_rejected(client, db, workflow, changes):
    response = client.post(
        f"/api/verifications/projects/{workflow['project'].id}/issue", json=ISSUE | changes
    )
    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(RegistryCredit)) == 0


def test_missing_approval_cannot_be_inferred_from_verified_status(client, db, login, make_project):
    login(Role.REGISTRY_STAFF)
    project = make_project()
    project.status = ProjectStatus.VERIFIED
    db.flush()
    assert (
        client.post(f"/api/verifications/projects/{project.id}/issue", json=ISSUE).status_code
        == 409
    )


def test_demo_records_are_hidden_outside_local_development(client, db, make_user, monkeypatch):
    from app.features.registry.demo import seed_registry_demo

    for role, email in (
        (Role.DEVELOPER, "developer"),
        (Role.REGISTRY_STAFF, "staff"),
        (Role.BUYER, "buyer"),
    ):
        make_user(role, email=f"{email}@crvr.local")
    seed_registry_demo(db)
    credit = db.scalar(select(RegistryCredit))
    assert client.get("/api/registry/credits").json()["total"] == 3
    for env in ("staging", "production"):
        monkeypatch.setattr(get_settings(), "app_env", env)
        assert client.get("/api/registry/credits").json()["total"] == 0
        assert client.get(f"/api/registry/credits/{credit.id}").status_code == 404
        assert client.get(f"/api/registry/credits/{credit.id}/integrity").status_code == 404
    monkeypatch.setattr(get_settings(), "app_env", "development")
    monkeypatch.setattr(get_settings(), "seed_demo_users", False)
    assert client.get("/api/registry/credits").json()["total"] == 0


def test_review_offers_issuing_to_staff_and_then_shows_the_batch(client, db, workflow):
    from app.features.verification.models import VerificationAssignment

    assignment = db.scalar(
        select(VerificationAssignment).where(
            VerificationAssignment.project_id == workflow["project"].id
        )
    )
    url = f"/api/verifications/assignments/{assignment.id}"
    sign_in(client, workflow["staff"])
    before = client.get(url).json()
    assert (before["can_issue"], before["buffer_percent"], before["issuance"]) == (True, 10, None)
    sign_in(client, workflow["verifier"])
    assert client.get(url).json()["can_issue"] is False

    credit = issue(client, workflow)

    after = client.get(url).json()
    assert after["can_issue"] is False
    assert after["issuance"] == {
        "credit_id": credit["id"],
        "vintage": ISSUE["vintage"],
        "quantity": 66,
        "buffer_quantity": 7,
    }
