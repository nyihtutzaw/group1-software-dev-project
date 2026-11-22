from fastapi import APIRouter, Depends, FastAPI

from app.auth.deps import get_current_user, require_roles
from app.auth.models import Role
from app.features.audit.access_matrix import build_access_matrix

ALL_ROLES = [role.value for role in Role]


def _endpoint(matrix: dict, method: str, path: str) -> dict:
    return next(e for e in matrix["endpoints"] if e["method"] == method and e["path"] == path)


def test_access_matrix_is_admin_only(client, login):
    assert client.get("/api/admin/access-matrix").status_code == 401
    for role in (Role.DEVELOPER, Role.VERIFIER, Role.REGISTRY_STAFF, Role.BUYER):
        login(role)
        assert client.get("/api/admin/access-matrix").status_code == 403


def test_access_matrix_reflects_the_route_role_checks(client, login):
    login(Role.ADMIN)

    response = client.get("/api/admin/access-matrix")

    assert response.status_code == 200
    matrix = response.json()
    assert matrix["roles"] == ALL_ROLES

    ledger = _endpoint(matrix, "GET", "/api/ledger")
    assert ledger["access"] == "roles"
    assert ledger["roles"] == ["verifier", "registry_staff", "buyer", "admin"]
    assert ledger["area"] == "F5 audit"

    assert _endpoint(matrix, "POST", "/api/projects")["roles"] == ["developer"]
    assert _endpoint(matrix, "GET", "/api/admin/access-matrix")["roles"] == ["admin"]

    me = _endpoint(matrix, "GET", "/api/auth/me")
    assert me["access"] == "signed_in"
    assert me["roles"] == ALL_ROLES

    login_route = _endpoint(matrix, "POST", "/api/auth/login")
    assert login_route["access"] == "public"


def test_access_matrix_combines_nested_role_checks():
    router = APIRouter(prefix="/api", tags=["demo"])

    @router.get("/staff", dependencies=[Depends(require_roles(Role.REGISTRY_STAFF, Role.ADMIN))])
    def staff_only(_user=Depends(require_roles(Role.ADMIN, Role.BUYER))) -> None:
        """Staff and admin, narrowed to admin."""

    @router.get("/me")
    def me(_user=Depends(get_current_user)) -> None: ...

    @router.get("/open")
    def open_route() -> None: ...

    admin_router = APIRouter(prefix="/api/admin", tags=["demo"])

    @admin_router.get("/report")
    def report() -> None: ...

    app = FastAPI()
    app.include_router(router)
    app.include_router(admin_router, dependencies=[Depends(require_roles(Role.ADMIN))])

    matrix = build_access_matrix(app.routes)
    by_path = {e.path: e for e in matrix.endpoints}

    assert by_path["/api/staff"].roles == [Role.ADMIN]
    assert by_path["/api/staff"].summary == "Staff and admin, narrowed to admin"
    assert by_path["/api/me"].access == "signed_in"
    assert by_path["/api/open"].access == "public"
    assert by_path["/api/open"].summary == "Open route"
    assert by_path["/api/admin/report"].roles == [Role.ADMIN]
