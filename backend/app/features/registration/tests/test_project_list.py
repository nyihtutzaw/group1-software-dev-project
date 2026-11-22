from app.auth.models import Role


def test_developer_sees_only_own_projects(client, login, make_project):
    me = login(Role.DEVELOPER)
    mine = make_project(owner=me, name="Mine")
    make_project(name="Someone else's")

    codes = [p["code"] for p in client.get("/api/projects").json()]

    assert codes == [mine.code]


def test_registry_staff_sees_all_projects(client, login, make_project):
    login(Role.REGISTRY_STAFF)
    make_project()
    make_project()

    assert len(client.get("/api/projects").json()) == 2


def test_buyer_cannot_list_projects(client, login):
    login(Role.BUYER)

    assert client.get("/api/projects").status_code == 403
