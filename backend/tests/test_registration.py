"""F1 registration and evidence — one test (or more) per acceptance criterion of issue #3."""

import hashlib
import stat

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError

from app.auth.models import Role
from app.core.config import get_settings
from app.features.boundary import service as boundary_service
from app.features.boundary.models import BoundarySource
from app.features.registration import service
from app.features.registration.models import EvidenceFile, Project
from tests.geo import BASE, square

COMPLETE = {
    "name": "Nan Reforestation Phase II",
    "methodology": "VM0047",
    "crediting_start_year": 2027,
    "crediting_end_year": 2047,
    "area_ha": 1240,
    "est_removal_tco2e": 24800,
    "baseline_summary": "Degraded grazing land, no natural regeneration recorded 2019–2026.",
    "additionality_reasoning": (
        "Without carbon finance the land stays as grazing: replanting costs exceed the "
        "returns from timber, and no regulation requires restoration."
    ),
}
PDF = b"%PDF-1.7 land title"


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    """Evidence goes to a temporary folder, not the dev volume."""
    monkeypatch.setattr(get_settings(), "storage_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
def ledger(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "record_action", lambda db, **kw: calls.append(kw))
    return calls


@pytest.fixture
def draft(client, login):
    """A developer signed in with a complete-looking draft (no evidence or boundary yet)."""
    developer = login(Role.DEVELOPER)
    project = client.post("/api/projects", json=COMPLETE).json()
    return developer, project


def upload(client, project_id, name="land-title.pdf", data=PDF, kind="land_title"):
    return client.post(
        f"/api/projects/{project_id}/evidence",
        files={"file": (name, data, "application/octet-stream")},
        data={"kind": kind},
    )


def draw_boundary(db, project_id, developer, geojson=None):
    project = db.get(Project, project_id)
    db.refresh(developer)  # expired by the API's commit; save_boundary flushes mid-way
    geojson = geojson or square(BASE[0] + 1, BASE[1])  # far from everything else
    boundary_service.save_boundary(db, project, geojson, BoundarySource.DRAWN, developer)


def make_ready(client, db, draft):
    developer, project = draft
    upload(client, project["id"])
    upload(client, project["id"], "additionality.pdf", kind="additionality_proof")
    draw_boundary(db, project["id"], developer)
    return project


# --- 4.1.1 drafts and validation ------------------------------------------------------


def test_developer_starts_a_draft_with_just_a_name(client, login, ledger):
    login(Role.DEVELOPER)

    res = client.post("/api/projects", json={"name": "Phetchabun Agroforestry"})

    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "draft"
    assert body["code"].startswith("CRVR-")
    assert body["can_edit"] is True
    assert "Methodology" in body["missing"]
    assert ledger[0]["action"] == "project.created"


def test_each_project_gets_its_own_code(client, login):
    login(Role.DEVELOPER)
    a = client.post("/api/projects", json={"name": "First"}).json()
    b = client.post("/api/projects", json={"name": "Second"}).json()
    assert a["code"] != b["code"]


@pytest.mark.parametrize(
    "change",
    [
        {"name": "ab"},
        {"methodology": "MADE-UP"},
        {"area_ha": -5},
        {"est_removal_tco2e": 0},
        {"crediting_start_year": 1850},
        {"unknown_field": 1},
    ],
)
def test_invalid_data_is_rejected(client, login, change):
    login(Role.DEVELOPER)
    assert client.post("/api/projects", json={**COMPLETE, **change}).status_code == 422


def test_crediting_period_must_end_after_it_starts(client, login):
    login(Role.DEVELOPER)

    res = client.post(
        "/api/projects",
        json={**COMPLETE, "crediting_start_year": 2040, "crediting_end_year": 2030},
    )

    assert res.status_code == 422
    assert res.json()["detail"] == "The crediting period must end after it starts"


def test_developer_saves_and_resumes_a_draft(client, draft):
    _, project = draft

    saved = client.put(
        f"/api/projects/{project['id']}", json={**COMPLETE, "area_ha": 1300.5}
    ).json()
    resumed = client.get(f"/api/projects/{project['id']}").json()

    assert saved["area_ha"] == resumed["area_ha"] == 1300.5
    assert resumed["status"] == "draft"


@pytest.mark.parametrize("role", [Role.REGISTRY_STAFF, Role.VERIFIER, Role.BUYER, Role.ADMIN])
def test_only_developers_register_projects(client, login, role):
    login(role)
    assert client.post("/api/projects", json=COMPLETE).status_code == 403


# --- 4.1.2 additionality ---------------------------------------------------------------


def test_additionality_reasoning_and_proof_are_stored(client, draft):
    _, project = draft

    upload(client, project["id"], "additionality-memo.pdf", kind="additionality_proof")
    body = client.get(f"/api/projects/{project['id']}").json()

    assert body["additionality_reasoning"] == COMPLETE["additionality_reasoning"]
    assert [e["kind"] for e in body["evidence"]] == ["additionality_proof"]
    assert "Additionality proof upload" not in body["missing"]


def test_short_additionality_reasoning_does_not_count(client, draft):
    _, project = draft
    client.put(f"/api/projects/{project['id']}", json={**COMPLETE, "additionality_reasoning": "x"})

    missing = client.get(f"/api/projects/{project['id']}").json()["missing"]

    assert any(m.startswith("Additionality reasoning") for m in missing)


# --- 4.2.1 evidence formats ------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("land-title-442-2561.pdf", "land_title"),
        ("plot-north.JPG", "photo"),
        ("IMG_0001.heic", "photo"),
        ("baseline-survey-2026.xlsx", "spreadsheet"),
        ("plots.csv", "spreadsheet"),
        ("walk.gpx", "gps"),
        ("boundary.kml", "gps"),
        ("site-photos-geotagged.zip", "photo"),
    ],
)
def test_accepted_evidence_formats(client, draft, storage, name, kind):
    _, project = draft

    res = upload(client, project["id"], name, b"evidence bytes", kind)

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["filename"] == name
    assert body["size_bytes"] == len(b"evidence bytes")
    assert body["sha256"] == hashlib.sha256(b"evidence bytes").hexdigest()


def test_other_formats_are_rejected_with_the_accepted_list(client, draft, storage):
    _, project = draft

    res = upload(client, project["id"], "setup.exe", b"MZ")

    assert res.status_code == 415
    assert "Accepted: PDF" in res.json()["detail"]
    assert not any(storage.rglob("*.exe"))


def test_empty_and_oversized_files_are_rejected_and_not_kept(client, draft, storage, monkeypatch):
    _, project = draft
    monkeypatch.setattr(get_settings(), "evidence_max_bytes", 10)

    assert upload(client, project["id"], data=b"").status_code == 422
    assert upload(client, project["id"], data=b"x" * 11).status_code == 413
    assert not [p for p in storage.rglob("*") if p.is_file()]
    assert client.get(f"/api/projects/{project['id']}").json()["evidence"] == []


def test_path_in_filename_is_stripped(client, draft):
    _, project = draft
    body = upload(client, project["id"], "../../etc/title.pdf").json()
    assert body["filename"] == "title.pdf"


# --- 4.2.2 write once ------------------------------------------------------------------


def test_evidence_is_sealed_read_only_on_disk(client, db, draft, storage, ledger):
    _, project = draft

    body = upload(client, project["id"]).json()

    stored = db.get(EvidenceFile, body["id"])
    path = storage / stored.storage_key
    assert path.read_bytes() == PDF
    assert not path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    assert body["sealed_at"]
    assert ledger[-1]["action"] == "evidence.sealed"
    assert ledger[-1]["payload"]["sha256"] == hashlib.sha256(PDF).hexdigest()


def test_api_offers_no_way_to_replace_or_delete_evidence(client, draft):
    _, project = draft
    evidence = upload(client, project["id"]).json()
    base = f"/api/projects/{project['id']}/evidence"

    for method in ("put", "patch", "delete"):
        for url in (base, f"{base}/{evidence['id']}", f"{base}/{evidence['id']}/file"):
            assert client.request(method, url).status_code in (404, 405)


@pytest.mark.parametrize("statement", ["update", "delete"])
def test_database_refuses_to_change_evidence_rows(client, db, draft, statement):
    _, project = draft
    upload(client, project["id"])
    stmt = (
        update(EvidenceFile).values(filename="forged.pdf")
        if statement == "update"
        else delete(EvidenceFile)
    )

    with pytest.raises(DBAPIError, match="write-once"), db.begin_nested():
        db.execute(stmt.where(EvidenceFile.project_id == project["id"]))


def test_owner_downloads_the_exact_bytes(client, draft):
    _, project = draft
    evidence = upload(client, project["id"]).json()

    res = client.get(f"/api/projects/{project['id']}/evidence/{evidence['id']}/file")

    assert res.status_code == 200
    assert res.content == PDF


# --- submission ------------------------------------------------------------------------


def test_incomplete_draft_cannot_be_submitted(client, login):
    login(Role.DEVELOPER)
    project = client.post("/api/projects", json={"name": "Half done"}).json()

    res = client.post(f"/api/projects/{project['id']}/submit")

    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail.startswith("This project cannot be submitted yet. Still needed: Methodology")
    assert "No boundary has been registered" in detail
    assert client.get(f"/api/projects/{project['id']}").json()["status"] == "draft"


def test_complete_draft_is_submitted_and_sealed(client, db, draft, ledger):
    project = make_ready(client, db, draft)
    assert client.get(f"/api/projects/{project['id']}").json()["missing"] == []

    res = client.post(f"/api/projects/{project['id']}/submit")

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "submitted"
    assert body["submitted_at"]
    assert body["can_edit"] is False
    submitted = [c for c in ledger if c["action"] == "project.submitted"]
    assert len(submitted[0]["payload"]["evidence_sha256"]) == 2


def test_submitted_project_can_no_longer_change(client, db, draft):
    project = make_ready(client, db, draft)
    client.post(f"/api/projects/{project['id']}/submit")
    pid = project["id"]

    assert client.put(f"/api/projects/{pid}", json=COMPLETE).status_code == 409
    assert upload(client, pid).status_code == 409
    assert client.post(f"/api/projects/{pid}/submit").status_code == 409


def test_overlapping_boundary_blocks_submission(client, db, draft, make_project, make_user):
    developer, project = draft
    upload(client, project["id"])
    upload(client, project["id"], "additionality.pdf", kind="additionality_proof")
    neighbour = make_project(name="Phrae Agroforestry")
    admin = make_user(Role.ADMIN, email="registrar@test.local")
    boundary_service.save_boundary(db, neighbour, square(*BASE), BoundarySource.DRAWN, admin)
    draw_boundary(db, project["id"], developer, square(BASE[0] + 0.0097, BASE[1]))

    res = client.post(f"/api/projects/{project['id']}/submit")

    assert res.status_code == 422
    assert "overlaps another project" in res.json()["detail"]
    listed = client.get("/api/projects").json()
    assert listed[0]["overlap"] is True


# --- 4.3.1 / visibility ----------------------------------------------------------------


def test_list_shows_live_status_and_evidence_count(client, draft):
    _, project = draft
    upload(client, project["id"])

    [row] = client.get("/api/projects").json()

    assert row["status"] == "draft"
    assert row["evidence_count"] == 1
    assert row["overlap"] is False
    assert row["methodology"] == "VM0047"


def test_developer_cannot_open_someone_elses_project(client, make_project, login):
    other = make_project()
    login(Role.DEVELOPER)

    assert client.get(f"/api/projects/{other.id}").status_code == 404
    assert client.put(f"/api/projects/{other.id}", json=COMPLETE).status_code == 404
    assert upload(client, other.id).status_code == 404


def test_registry_staff_see_drafts_but_cannot_change_them(client, make_project, login):
    project = make_project()
    login(Role.REGISTRY_STAFF)

    body = client.get(f"/api/projects/{project.id}").json()

    assert body["status"] == "draft"
    assert body["can_edit"] is False
    assert client.put(f"/api/projects/{project.id}", json=COMPLETE).status_code == 403


def test_verifiers_see_submitted_projects_only(client, db, make_project, login):
    draft_project = make_project()
    submitted = make_project()
    submitted.status = "submitted"
    db.flush()
    login(Role.VERIFIER)

    assert client.get(f"/api/projects/{draft_project.id}").status_code == 404
    assert client.get(f"/api/projects/{submitted.id}").status_code == 200


def test_buyers_cannot_open_projects(client, make_project, login):
    project = make_project()
    login(Role.BUYER)
    assert client.get(f"/api/projects/{project.id}").status_code == 403
