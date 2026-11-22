"""System › Demo data: an admin resets the demo server to the live-demo start or full data."""

from sqlalchemy import select

from app.auth.models import Role
from app.core.config import get_settings
from app.features.audit.ledger import verify_ledger_chain
from app.features.audit.models import LedgerEntry
from app.features.registration.models import Project

# Nam Wa's boundaries, as in frontend/public/tutorials/samples/
NAM_WA_FINAL = {
    "type": "Polygon",
    "coordinates": [
        [
            [100.8535, 18.786],
            [100.852, 18.7985],
            [100.865, 18.803],
            [100.8755, 18.795],
            [100.871, 18.7845],
            [100.8535, 18.786],
        ]
    ],
}
NAM_WA_DRAFT = {
    "type": "Polygon",
    "coordinates": [
        [
            [100.8558, 18.7863],
            [100.8544, 18.7983],
            [100.865, 18.8027],
            [100.8815, 18.7955],
            [100.871, 18.7848],
            [100.8558, 18.7863],
        ]
    ],
}


def reset(client, start: str, confirm: str = "RESET"):
    return client.post("/api/admin/demo-data/reset", json={"start": start, "confirm": confirm})


def sign_in(client, email: str) -> None:
    password = get_settings().demo_password
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text


def test_only_admins_see_and_reset_demo_data(client, login):
    assert client.get("/api/admin/demo-data").status_code == 401
    for role in (Role.DEVELOPER, Role.VERIFIER, Role.REGISTRY_STAFF, Role.BUYER):
        login(role)
        assert client.get("/api/admin/demo-data").status_code == 403
        assert reset(client, "live").status_code == 403


def test_admin_sees_whether_reset_is_allowed_and_the_counts(client, login):
    login(Role.ADMIN)

    body = client.get("/api/admin/demo-data").json()

    assert body["enabled"] is True
    assert set(body["counts"]) == {"users", "projects", "boundaries", "credits", "ledger_entries"}


def test_reset_is_refused_on_a_real_registry(client, login, monkeypatch):
    login(Role.ADMIN)
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "demo_mode", False)

    assert client.get("/api/admin/demo-data").json()["enabled"] is False
    res = reset(client, "live")

    assert res.status_code == 403
    assert "demo server" in res.json()["detail"]


def test_reset_needs_the_typed_confirmation(client, login, make_project):
    login(Role.ADMIN)
    make_project()

    res = reset(client, "live", confirm="reset please")

    assert res.status_code == 422
    assert client.get("/api/admin/demo-data").json()["counts"]["projects"] >= 1


def test_live_start_leaves_accounts_and_the_neighbour_only(client, db, login, make_project):
    login(Role.ADMIN)
    make_project(name="Left over from testing")

    res = reset(client, "live")

    assert res.status_code == 200, res.text
    assert res.json()["counts"] == {
        "users": 6,
        "projects": 1,
        "boundaries": 1,
        "credits": 0,
        "ledger_entries": 2,  # the reset, then the neighbour's boundary
    }
    project = db.scalar(select(Project))
    assert (project.code, project.name, project.status) == (
        "CRVR-0174",
        "Huai Nam Rin Community Forest",
        "submitted",
    )
    first = db.scalar(select(LedgerEntry).order_by(LedgerEntry.id))
    assert first.action == "demo_data.reset"
    assert first.payload == {"start": "live", "requested_by": "admin@test.local"}
    assert verify_ledger_chain(db) == (True, None)


def test_live_start_numbers_new_projects_from_200(client, login):
    login(Role.ADMIN)
    reset(client, "live")
    sign_in(client, "developer@crvr.local")

    res = client.post("/api/projects", json={"name": "Nam Wa Hillside Reforestation"})

    assert res.status_code == 201, res.text
    assert res.json()["code"] == "CRVR-0200"


def test_sample_boundaries_overlap_the_neighbour_only_in_the_first_survey(client, login):
    login(Role.ADMIN)
    reset(client, "live")
    sign_in(client, "developer@crvr.local")

    draft = client.post("/api/boundaries/check", json={"geometry": NAM_WA_DRAFT}).json()
    final = client.post("/api/boundaries/check", json={"geometry": NAM_WA_FINAL}).json()

    assert draft["blocked"] is True
    [overlap] = draft["overlaps"]
    assert overlap["project_code"] == "CRVR-0174"
    assert 4 < overlap["overlap_pct"] < 5
    assert final["blocked"] is False
    assert final["overlaps"] == []


def test_full_start_loads_the_sample_data(client, login):
    login(Role.ADMIN)

    res = reset(client, "full")

    assert res.status_code == 200, res.text
    counts = res.json()["counts"]
    assert counts["users"] == 6
    assert counts["projects"] == 5
    assert counts["credits"] == 3
