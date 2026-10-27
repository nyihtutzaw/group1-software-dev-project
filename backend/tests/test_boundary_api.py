import json

import pytest

from app.auth.models import Role
from app.core.config import get_settings
from app.features.boundary import service
from app.features.boundary.models import BoundarySource, FlagStatus, OverlapFlag
from tests.geo import BASE, square

OVERLAPPING = square(BASE[0] + 0.0097, BASE[1])  # 3% of its area inside BASE
CLEAR = square(BASE[0] + 0.02, BASE[1])


@pytest.fixture
def registered(db, make_project, make_user):
    """A project that already has a boundary (registered by an admin)."""
    admin = make_user(Role.ADMIN, email="registrar@test.local")

    def _registered(geojson=None, name="Phrae Agroforestry", owner=None):
        project = make_project(owner=owner, name=name)
        service.save_boundary(db, project, geojson or square(*BASE), BoundarySource.DRAWN, admin)
        return project

    return _registered


@pytest.fixture
def ledger(monkeypatch):
    """Capture record_action calls."""
    calls = []
    monkeypatch.setattr(service, "record_action", lambda db, **kw: calls.append(kw))
    return calls


# --- access ---------------------------------------------------------------------------


def test_map_requires_sign_in(client):
    assert client.get("/api/boundaries").status_code == 401


def test_buyers_cannot_use_the_map(client, login):
    login(Role.BUYER)

    assert client.get("/api/boundaries").status_code == 403
    assert client.post("/api/boundaries/check", json={"geometry": CLEAR}).status_code == 403


@pytest.mark.parametrize("role", [Role.VERIFIER, Role.REGISTRY_STAFF])
def test_reviewers_can_view_but_not_change_boundaries(client, login, registered, role):
    project = registered()
    login(role)

    assert client.get(f"/api/boundaries/{project.id}").json()["can_edit"] is False
    res = client.put(f"/api/boundaries/{project.id}", json={"geometry": CLEAR})
    assert res.status_code == 403


def test_developer_cannot_touch_someone_elses_project(client, login, registered):
    project = registered()
    login(Role.DEVELOPER)

    assert client.get(f"/api/boundaries/{project.id}").status_code == 403
    assert client.put(f"/api/boundaries/{project.id}", json={"geometry": CLEAR}).status_code == 403


def test_unknown_project_is_404(client, login):
    login(Role.ADMIN)

    assert client.put("/api/boundaries/999999", json={"geometry": CLEAR}).status_code == 404


# --- list and check -------------------------------------------------------------------


def test_list_returns_registered_boundaries_as_geojson(client, login, registered):
    project = registered()
    login(Role.VERIFIER)

    body = client.get("/api/boundaries").json()

    assert body["type"] == "FeatureCollection"
    [feature] = body["features"]
    assert feature["geometry"]["type"] == "MultiPolygon"
    assert feature["properties"]["code"] == project.code
    assert feature["properties"]["flagged"] is False


def test_check_reports_overlap_without_saving(client, login, registered):
    other = registered()
    login(Role.DEVELOPER)

    body = client.post("/api/boundaries/check", json={"geometry": OVERLAPPING}).json()

    assert body["blocked"] is True
    assert body["checked_against"] == 1
    assert body["tolerance_pct"] == 0.5
    [overlap] = body["overlaps"]
    assert overlap["project_code"] == other.code
    assert overlap["overlap_pct"] == pytest.approx(3.0, abs=0.01)
    assert overlap["overlap_ha"] == pytest.approx(body["area_ha"] * 0.03, rel=0.001)
    assert len(client.get("/api/boundaries").json()["features"]) == 1


def test_check_rejects_invalid_shapes_with_a_message(client, login):
    login(Role.DEVELOPER)
    bowtie = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}

    res = client.post("/api/boundaries/check", json={"geometry": bowtie})

    assert res.status_code == 422
    assert "Self-intersection" in res.json()["detail"]


# --- save -----------------------------------------------------------------------------


def test_developer_saves_a_clear_boundary(client, login, make_project, registered, ledger):
    registered()
    me = login(Role.DEVELOPER)
    project = make_project(owner=me)
    ledger.clear()

    res = client.put(
        f"/api/boundaries/{project.id}", json={"geometry": CLEAR, "source": "uploaded"}
    )

    body = res.json()
    assert res.status_code == 200
    assert body["can_edit"] is True
    assert body["source"] == "uploaded"
    assert body["flags"] == []
    assert body["issuance_blocked"] is None
    assert body["check"]["area_ha"] > 100
    assert [c["action"] for c in ledger] == ["boundary.saved"]


def test_overlap_above_tolerance_is_flagged_and_blocks_issuance(
    client, login, make_project, registered, ledger
):
    other = registered()
    me = login(Role.DEVELOPER)
    project = make_project(owner=me)
    ledger.clear()

    body = client.put(f"/api/boundaries/{project.id}", json={"geometry": OVERLAPPING}).json()

    [flag] = body["flags"]
    assert flag["other_project_code"] == other.code
    assert flag["status"] == "open"
    assert flag["overlap_pct"] == pytest.approx(3.0, abs=0.01)
    assert "overlaps another project" in body["issuance_blocked"]
    assert [c["action"] for c in ledger] == ["boundary.saved", "boundary.overlap_detected"]
    assert ledger[1]["actor"] is None  # detected by the system
    assert client.get("/api/boundaries").json()["features"][1]["properties"]["flagged"] is True


def test_redrawing_clear_supersedes_the_flag(client, login, make_project, registered, db):
    registered()
    me = login(Role.DEVELOPER)
    project = make_project(owner=me)
    client.put(f"/api/boundaries/{project.id}", json={"geometry": OVERLAPPING})

    body = client.put(f"/api/boundaries/{project.id}", json={"geometry": CLEAR}).json()

    assert body["flags"] == []
    assert body["issuance_blocked"] is None
    old = db.query(OverlapFlag).filter_by(project_id=project.id).one()
    assert old.status == FlagStatus.SUPERSEDED


def test_get_boundary_without_one_is_404(client, login, make_project):
    me = login(Role.DEVELOPER)
    project = make_project(owner=me)

    assert client.get(f"/api/boundaries/{project.id}").status_code == 404


# --- dispute and resolve --------------------------------------------------------------


@pytest.fixture
def flagged(client, login, make_project, registered):
    """The signed-in developer's project, saved overlapping another one. Returns (project, flag)."""
    registered()
    me = login(Role.DEVELOPER)
    project = make_project(owner=me)
    body = client.put(f"/api/boundaries/{project.id}", json={"geometry": OVERLAPPING}).json()
    return project, body["flags"][0]


def test_developer_disputes_an_overlap(client, flagged):
    project, flag = flagged

    res = client.post(
        f"/api/boundaries/flags/{flag['id']}/dispute",
        json={"reason": "CRVR-0092's survey is from 2009 and misplaces the river."},
    )

    assert res.json()["status"] == "disputed"
    assert client.get(f"/api/boundaries/{project.id}").json()["issuance_blocked"]  # still blocked
    again = client.post(
        f"/api/boundaries/flags/{flag['id']}/dispute", json={"reason": "Trying a second time."}
    )
    assert again.status_code == 409


def test_dispute_needs_a_real_reason(client, flagged):
    _, flag = flagged

    res = client.post(f"/api/boundaries/flags/{flag['id']}/dispute", json={"reason": "no"})

    assert res.status_code == 422


def test_staff_resolve_an_overlap_and_unblock_issuance(client, login, flagged, db):
    project, flag = flagged
    login(Role.REGISTRY_STAFF)

    res = client.post(
        f"/api/boundaries/flags/{flag['id']}/resolve",
        json={"note": "Site visit confirmed the river line; CRVR-0092 to be corrected."},
    )

    assert res.json()["status"] == "resolved"
    assert service.issuance_blocked(db, project.id) is None


def test_developer_cannot_resolve_their_own_flag(client, flagged):
    _, flag = flagged

    res = client.post(f"/api/boundaries/flags/{flag['id']}/resolve", json={"note": "All fine."})

    assert res.status_code == 403


def test_nobody_resolves_a_flag_on_their_own_project(client, login, make_project, registered):
    registered()
    admin = login(Role.ADMIN)
    own = make_project(owner=admin)
    flag = client.put(f"/api/boundaries/{own.id}", json={"geometry": OVERLAPPING}).json()["flags"][
        0
    ]

    res = client.post(f"/api/boundaries/flags/{flag['id']}/resolve", json={"note": "Mine, OK."})

    assert res.status_code == 403
    assert "your own project" in res.json()["detail"]


# --- import ---------------------------------------------------------------------------


def test_import_reads_a_geojson_file(client, login):
    login(Role.DEVELOPER)
    data = json.dumps({"type": "Feature", "geometry": CLEAR}).encode()

    res = client.post(
        "/api/boundaries/import", files={"file": ("parcel.geojson", data, "application/json")}
    )

    assert res.status_code == 200
    assert res.json() == {"filename": "parcel.geojson", "geometry": CLEAR}


def test_import_rejects_unsupported_files(client, login):
    login(Role.DEVELOPER)

    res = client.post("/api/boundaries/import", files={"file": ("survey.pdf", b"%PDF", "x")})

    assert res.status_code == 422


def test_import_rejects_large_files(client, login, monkeypatch):
    login(Role.DEVELOPER)
    monkeypatch.setattr(get_settings(), "boundary_upload_max_bytes", 10)

    res = client.post("/api/boundaries/import", files={"file": ("a.geojson", b"x" * 11, "x")})

    assert res.status_code == 413


# --- issuance gate --------------------------------------------------------------------


def test_issuance_is_blocked_without_a_boundary(db, make_project):
    assert "No boundary" in service.issuance_blocked(db, make_project().id)
