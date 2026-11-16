"""Real F1 → F3 approval → issuance → F4 reads, including privacy and atomicity."""

import hashlib
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from app.auth.models import Role
from app.core.config import get_settings
from app.features.audit.ledger import verify_ledger_chain
from app.features.audit.models import LedgerEntry
from app.features.boundary.models import BoundarySource, FlagStatus, OverlapFlag
from app.features.boundary.service import save_boundary
from app.features.registration.models import Project, ProjectStatus
from app.features.registration.service import buyer_evidence_summaries
from app.features.registry.models import RegistryCredit, RegistryCreditEvent, RegistryProjectAccess
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
    assert credit["quantity"] == ISSUE["quantity"] != workflow["project"].est_removal_tco2e
    row = db.get(RegistryCredit, credit["id"])
    assert row.source_project_id == workflow["project"].id
    assert row.source_approval_id == workflow["approval_id"]
    assert not row.is_demo
    client.post("/api/auth/logout")
    results = client.get("/api/registry/credits", params={"q": workflow["project"].code}).json()
    assert results["total"] == 1
    assert results["items"][0] == credit
    detail = client.get(f"/api/registry/credits/{credit['id']}").json()
    assert detail["history"][0]["action"] == "issued"
    assert client.get(f"/api/registry/credits/{credit['id']}/integrity").json()["snapshot_matches"]
    entry = db.scalar(select(LedgerEntry).where(LedgerEntry.action == "credit.issued"))
    assert entry.payload["serial"] == credit["serial"]
    assert entry.payload["quantity"] == 73
    assert verify_ledger_chain(db) == (True, None)
    duplicate = (
        sign_in(client, workflow["staff"]),
        client.post(f"/api/verifications/projects/{workflow['project'].id}/issue", json=ISSUE),
    )[1]
    assert duplicate.status_code == 409
    assert db.scalar(select(func.count()).select_from(RegistryCredit)) == 1
    assert db.scalar(select(func.count()).select_from(RegistryCreditEvent)) == 1


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
