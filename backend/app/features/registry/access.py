"""Buyer access administration (#30): registry staff grant and revoke project access.

Grants live in ``registry_project_access`` (default deny) and are read on every registry
request, so a change applies to the buyer's next load. Each change is sealed in the F5 ledger.
Kept in its own module (schemas, service and routes) so the registry read path stays unchanged.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.db import get_db
from app.features.audit.ledger import record_action
from app.features.registry.models import RegistryProjectAccess
from app.features.registry.service import _visible_credits

STAFF = (Role.REGISTRY_STAFF, Role.ADMIN)


class AccessGrantIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    project_reference: str = Field(min_length=1, max_length=80)
    buyer_id: int = Field(gt=0)


class AccessGrantOut(BaseModel):
    project_reference: str
    # None when the reference has no visible publication (e.g. demo rows outside development).
    project_name: str | None
    buyer_id: int
    buyer_name: str
    buyer_email: str
    buyer_organization: str | None
    buyer_active: bool


class BuyerOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    organization: str | None


class ProjectOption(BaseModel):
    project_reference: str
    project_name: str


class AccessOptionsOut(BaseModel):
    buyers: list[BuyerOption]
    projects: list[ProjectOption]


def _staff(actor: User) -> None:
    if not actor.is_active or actor.role not in STAFF:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Registry staff access required")


def _published_projects(db: Session) -> dict[str, str]:
    """Project references that have a visible published credit, with a display name."""
    credits = _visible_credits().subquery()
    rows = db.execute(
        select(credits.c.project_reference, func.max(credits.c.project_name))
        .group_by(credits.c.project_reference)
        .order_by(credits.c.project_reference)
    ).all()
    return {reference: name for reference, name in rows}


def access_options(db: Session, actor: User) -> AccessOptionsOut:
    _staff(actor)
    buyers = db.scalars(
        select(User)
        .where(User.role == Role.BUYER, User.is_active.is_(True))
        .order_by(User.full_name, User.id)
    ).all()
    return AccessOptionsOut(
        buyers=[BuyerOption.model_validate(buyer) for buyer in buyers],
        projects=[
            ProjectOption(project_reference=reference, project_name=name)
            for reference, name in _published_projects(db).items()
        ],
    )


def list_grants(db: Session, actor: User) -> list[AccessGrantOut]:
    _staff(actor)
    names = _published_projects(db)
    rows = db.execute(
        select(RegistryProjectAccess, User)
        .join(User, User.id == RegistryProjectAccess.buyer_id)
        .order_by(RegistryProjectAccess.project_reference, User.full_name, User.id)
    ).all()
    return [_grant_out(grant, buyer, names) for grant, buyer in rows]


def _grant_out(grant: RegistryProjectAccess, buyer: User, names: dict[str, str]) -> AccessGrantOut:
    return AccessGrantOut(
        project_reference=grant.project_reference,
        project_name=names.get(grant.project_reference),
        buyer_id=buyer.id,
        buyer_name=buyer.full_name,
        buyer_email=buyer.email,
        buyer_organization=buyer.organization,
        buyer_active=buyer.is_active,
    )


def grant_access(db: Session, actor: User, data: AccessGrantIn) -> AccessGrantOut:
    _staff(actor)
    names = _published_projects(db)
    if data.project_reference not in names:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No published credits for this project")
    buyer = db.get(User, data.buyer_id)
    if buyer is None or buyer.role != Role.BUYER or not buyer.is_active:
        # Access grants are buyer entitlements only; other roles have their own permissions.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active buyer account")
    grant = RegistryProjectAccess(project_reference=data.project_reference, buyer_id=buyer.id)
    try:
        with db.begin_nested():
            db.add(grant)
            db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This buyer already has access to this project"
        ) from exc
    record_action(
        db,
        actor=actor,
        action="registry_access.granted",
        entity="user",
        entity_id=buyer.id,
        payload={"project_reference": grant.project_reference},
    )
    db.commit()
    return _grant_out(grant, buyer, names)


def revoke_access(db: Session, actor: User, project_reference: str, buyer_id: int) -> None:
    _staff(actor)
    grant = db.scalar(
        select(RegistryProjectAccess)
        .where(
            RegistryProjectAccess.project_reference == project_reference,
            RegistryProjectAccess.buyer_id == buyer_id,
        )
        .with_for_update()
    )
    if grant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Access grant not found")
    db.delete(grant)
    db.flush()
    record_action(
        db,
        actor=actor,
        action="registry_access.revoked",
        entity="user",
        entity_id=buyer_id,
        payload={"project_reference": project_reference},
    )
    db.commit()


router = APIRouter(prefix="/access", tags=["F4 registry"])


@router.get("", response_model=list[AccessGrantOut])
def get_grants(
    db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))
) -> list[AccessGrantOut]:
    return list_grants(db, user)


@router.get("/options", response_model=AccessOptionsOut)
def get_options(
    db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))
) -> AccessOptionsOut:
    return access_options(db, user)


@router.post("", response_model=AccessGrantOut, status_code=status.HTTP_201_CREATED)
def post_grant(
    body: AccessGrantIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*STAFF)),
) -> AccessGrantOut:
    return grant_access(db, user, body)


@router.delete("/{project_reference}/{buyer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grant(
    project_reference: str,
    buyer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*STAFF)),
) -> Response:
    revoke_access(db, user, project_reference, buyer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
