"""F5 role & access matrix — which role may call which API endpoint, read from the routes.

Every protected route declares its roles with `Depends(require_roles(...))`; `require_roles` tags
its checker with `allowed_roles`. Walking the mounted routes' dependency trees therefore gives the
access matrix the server really enforces, with no hand-kept copy to drift. Finer rules applied
inside services (a developer only sees their own projects, a verifier only their assignments) are
not visible here.
"""

from collections.abc import Sequence
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts
from pydantic import BaseModel
from starlette.routing import BaseRoute

from app.auth.deps import get_current_user, require_roles
from app.auth.models import Role, User

Access = Literal["public", "signed_in", "roles"]


class EndpointAccessOut(BaseModel):
    method: str
    path: str
    summary: str
    area: str
    access: Access
    roles: list[Role]


class AccessMatrixOut(BaseModel):
    roles: list[Role]
    endpoints: list[EndpointAccessOut]


router = APIRouter(prefix="/admin", tags=["F5 access control"])


def _route_access(dependant: Dependant) -> tuple[Access, list[Role]]:
    """Public, any signed-in user, or only the roles every `require_roles` on the route allows."""
    allowed: set[Role] | None = None
    signed_in = False
    stack = [dependant]
    while stack:
        for dep in stack.pop().dependencies:
            roles = getattr(dep.call, "allowed_roles", None)
            if roles is not None:
                allowed = set(roles) if allowed is None else allowed & set(roles)
            if dep.call is get_current_user:
                signed_in = True
            stack.append(dep)
    if allowed is not None:
        return "roles", [role for role in Role if role in allowed]
    return ("signed_in" if signed_in else "public"), list(Role)


def _summary(route: RouteContext) -> str:
    if route.summary:
        return route.summary
    if route.description:
        return route.description.strip().splitlines()[0].rstrip(".")
    return route.name.replace("_", " ").capitalize()


def build_access_matrix(routes: Sequence[BaseRoute]) -> AccessMatrixOut:
    endpoints = []
    # Included routers are mounted lazily; iterate their effective routes the way FastAPI's own
    # OpenAPI generator does, so prefixes and router-level dependencies are applied.
    for route in iter_route_contexts(routes):
        if not isinstance(route.original_route, APIRoute) or not str(route.path).startswith(
            "/api/"
        ):
            continue
        access, roles = _route_access(route.dependant)
        for method in sorted((route.methods or set()) - {"HEAD", "OPTIONS"}):
            endpoints.append(
                EndpointAccessOut(
                    method=method,
                    path=str(route.path),
                    summary=_summary(route),
                    area=str(route.tags[0]) if route.tags else "other",
                    access=access,
                    roles=roles,
                )
            )
    return AccessMatrixOut(roles=list(Role), endpoints=endpoints)


@router.get("/access-matrix", response_model=AccessMatrixOut)
def get_access_matrix(
    request: Request, _admin: User = Depends(require_roles(Role.ADMIN))
) -> AccessMatrixOut:
    """Read-only role & access matrix of the API."""
    return build_access_matrix(request.app.routes)
