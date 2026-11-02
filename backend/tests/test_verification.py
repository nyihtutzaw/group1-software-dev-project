"""F3 verification queue, structured report, and maker-checker."""

from datetime import date, timedelta

from app.auth.models import Role
from app.features.verification.models import CHECKLIST, VerificationReport
from tests.conftest import PASSWORD

DUE = date.today() + timedelta(days=10)


def sign_in(client, user):
    res = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return user


def report_body(decision="sign_off", note="Checked the project record and the boundary."):
    return {
        "checklist": {key: True for key, _label in CHECKLIST},
        "note": note,
        "decision": decision,
    }


def assign(client, project, verifier, due=DUE):
    res = client.post(
        "/api/verifications/assignments",
        json={"project_id": project.id, "verifier_id": verifier.id, "due_date": due.isoformat()},
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_verifier_sees_only_their_projects_oldest_due_first(client, login, make_user, make_project):
    staff = login(Role.REGISTRY_STAFF)
    mine = make_user(Role.VERIFIER, email="mine@test.local")
    other = make_user(Role.VERIFIER, email="other@test.local")
    later = make_project(name="Later")
    sooner = make_project(name="Sooner")
    hidden = make_project(name="Hidden")
    assign(client, later, mine, date.today() + timedelta(days=3))
    assign(client, sooner, mine, date.today() - timedelta(days=2))
    assign(client, hidden, other, date.today())

    sign_in(client, mine)
    body = client.get("/api/verifications/queue").json()

    assert [item["project_name"] for item in body["items"]] == ["Sooner", "Later"]
    assert body["items"][0]["overdue"] is True
    assert body["items"][0]["chip"] == "OVERDUE"
    assert body["items"][0]["days_overdue"] == 2
    assert body["items"][1]["overdue"] is False
    assert body["assigned_count"] == 2
    assert body["overdue_count"] == 1
    assert staff.id != mine.id


def test_due_today_is_not_overdue_and_staff_see_every_row(client, login, make_user, make_project):
    login(Role.REGISTRY_STAFF)
    verifier = make_user(Role.VERIFIER, email="v@test.local")
    assign(client, make_project(name="Today"), verifier, date.today())
    assign(client, make_project(name="Yesterday"), verifier, date.today() - timedelta(days=1))

    body = client.get("/api/verifications/queue").json()

    by_name = {item["project_name"]: item for item in body["items"]}
    assert by_name["Today"]["overdue"] is False
    assert by_name["Yesterday"]["overdue"] is True
    assert body["assigned_count"] == 2


def test_developer_and_buyer_cannot_open_the_queue(client, login):
    login(Role.DEVELOPER)
    assert client.get("/api/verifications/queue").status_code == 403
    login(Role.BUYER)
    assert client.get("/api/verifications/queue").status_code == 403


def test_only_staff_can_assign_an_active_verifier(client, login, make_user, make_project):
    verifier = make_user(Role.VERIFIER, email="v@test.local")
    developer = make_user(Role.DEVELOPER, email="dev@test.local")
    project = make_project()
    login(Role.VERIFIER)
    denied = client.post(
        "/api/verifications/assignments",
        json={
            "project_id": project.id,
            "verifier_id": verifier.id,
            "due_date": DUE.isoformat(),
        },
    )
    assert denied.status_code == 403

    login(Role.ADMIN)
    bad_role = client.post(
        "/api/verifications/assignments",
        json={
            "project_id": project.id,
            "verifier_id": developer.id,
            "due_date": DUE.isoformat(),
        },
    )
    assert bad_role.status_code == 422

    created = assign(client, project, verifier)
    assert created["project_code"] == project.code
    again = client.post(
        "/api/verifications/assignments",
        json={
            "project_id": project.id,
            "verifier_id": verifier.id,
            "due_date": DUE.isoformat(),
        },
    )
    assert again.status_code == 409


def test_other_verifier_cannot_open_or_submit(client, login, make_user, make_project):
    login(Role.REGISTRY_STAFF)
    owner = make_user(Role.VERIFIER, email="owner@test.local")
    stranger = make_user(Role.VERIFIER, email="stranger@test.local")
    created = assign(client, make_project(), owner)

    sign_in(client, stranger)
    assert client.get(f"/api/verifications/assignments/{created['id']}").status_code == 403
    denied = client.post(
        f"/api/verifications/assignments/{created['id']}/report",
        json=report_body(),
    )
    assert denied.status_code == 403

    sign_in(client, owner)
    opened = client.get(f"/api/verifications/assignments/{created['id']}")
    assert opened.status_code == 200
    review = opened.json()
    assert review["can_submit"] is True
    assert any(check["name"] == "Boundary overlap" for check in review["automatic_checks"])
    assert [line["key"] for line in review["checklist"]] == [key for key, _label in CHECKLIST]


def test_sign_off_is_irreversible_and_written_to_the_ledger(
    client, login, make_user, make_project, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        "app.features.verification.service.record_action",
        lambda db, **kw: calls.append(kw),
    )
    login(Role.REGISTRY_STAFF)
    verifier = make_user(Role.VERIFIER, email="v@test.local")
    created = assign(client, make_project(), verifier)
    sign_in(client, verifier)

    signed = client.post(
        f"/api/verifications/assignments/{created['id']}/report",
        json=report_body(),
    )
    assert signed.status_code == 200, signed.text
    body = signed.json()
    assert body["can_submit"] is False
    assert body["item"]["status"] == "signed_off"
    assert calls[-1]["action"] == "verification.signed_off"
    assert calls[-1]["actor"].email == verifier.email

    again = client.post(
        f"/api/verifications/assignments/{created['id']}/report",
        json=report_body(note="Trying to change a sign-off."),
    )
    assert again.status_code == 409


def test_request_changes_reaches_the_project_owner(client, login, make_user, make_project):
    login(Role.REGISTRY_STAFF)
    verifier = make_user(Role.VERIFIER, email="v@test.local")
    owner = make_user(Role.DEVELOPER, email="owner@test.local")
    project = make_project(owner=owner, name="Nan Reforestation Phase II")
    created = assign(client, project, verifier)
    sign_in(client, verifier)
    note = "Land title name does not match the applicant."
    submitted = client.post(
        f"/api/verifications/assignments/{created['id']}/report",
        json=report_body("request_changes", note),
    )
    assert submitted.status_code == 200, submitted.text

    sign_in(client, owner)
    notes = client.get("/api/verifications/notes").json()
    assert notes == [
        {
            "project_id": project.id,
            "project_code": project.code,
            "project_name": project.name,
            "note": note,
            "at": notes[0]["at"],
        }
    ]
    chain = client.get(f"/api/verifications/projects/{project.id}/chain").json()
    assert chain["chain"][1]["summary"] == "Requested changes"
    assert chain["chain"][1]["note"] == note

    sign_in(client, verifier)
    follow_up = client.post(
        f"/api/verifications/assignments/{created['id']}/report",
        json=report_body(),
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["item"]["status"] == "signed_off"


def test_maker_and_submitter_cannot_approve(client, login, db, make_user, make_project):
    approver = login(Role.REGISTRY_STAFF)
    verifier = make_user(Role.VERIFIER, email="v@test.local")
    project = make_project()
    created = assign(client, project, verifier)
    sign_in(client, verifier)
    signed = client.post(
        f"/api/verifications/assignments/{created['id']}/report",
        json=report_body(),
    )
    report_id = signed.json()["report_id"]

    report = db.get(VerificationReport, report_id)
    report.verifier_id = approver.id
    db.flush()
    sign_in(client, approver)
    own_sign_off = client.post(
        f"/api/verifications/reports/{report_id}/decision",
        json={"decision": "approved", "rationale": "Looks complete to me."},
    )
    assert own_sign_off.status_code == 403
    assert "signed off" in own_sign_off.json()["detail"]

    owner_staff = make_user(Role.REGISTRY_STAFF, email="owner-staff@test.local")
    owned = make_project(owner=owner_staff, name="Owned by staff")
    sign_in(client, approver)
    owned_assignment = assign(client, owned, verifier)
    sign_in(client, verifier)
    owned_report = client.post(
        f"/api/verifications/assignments/{owned_assignment['id']}/report",
        json=report_body(),
    )
    sign_in(client, owner_staff)
    own_project = client.post(
        f"/api/verifications/reports/{owned_report.json()['report_id']}/decision",
        json={"decision": "approved", "rationale": "I submitted this project."},
    )
    assert own_project.status_code == 403
    assert "submitted" in own_project.json()["detail"]


def test_other_staff_approve_and_the_chain_is_complete(
    client, login, make_user, make_project, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        "app.features.verification.service.record_action",
        lambda db, **kw: calls.append(kw),
    )
    login(Role.REGISTRY_STAFF)
    verifier = make_user(Role.VERIFIER, email="v@test.local")
    project = make_project(name="Nan Reforestation Phase II")
    created = assign(client, project, verifier)
    sign_in(client, verifier)
    signed = client.post(
        f"/api/verifications/assignments/{created['id']}/report",
        json=report_body(),
    )
    report_id = signed.json()["report_id"]

    checker = make_user(Role.REGISTRY_STAFF, email="checker@test.local")
    sign_in(client, checker)
    approved = client.post(
        f"/api/verifications/reports/{report_id}/decision",
        json={"decision": "approved", "rationale": "Separate reviewer. Evidence matches."},
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["item"]["status"] == "approved"
    assert body["approval"]["rationale"] == "Separate reviewer. Evidence matches."
    assert body["can_decide"] is False
    assert calls[-1]["action"] == "verification.approved"

    chain = client.get(f"/api/verifications/projects/{project.id}/chain").json()
    assert [event["kind"] for event in chain["chain"]] == ["assigned", "report", "approval"]

    second = client.post(
        f"/api/verifications/reports/{report_id}/decision",
        json={"decision": "rejected", "rationale": "Too late to change it."},
    )
    assert second.status_code == 409


def test_buyer_cannot_read_the_chain(client, login, make_project):
    project = make_project()
    login(Role.BUYER)
    assert client.get(f"/api/verifications/projects/{project.id}/chain").status_code == 403
