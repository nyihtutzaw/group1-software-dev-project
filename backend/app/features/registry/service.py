"""Public read model and trusted handoff functions for F1/F3 integration.

No HTTP write routes: F3 must validate approval/issuance before calling publish_credit.
F1 supplies an allowlisted projection of real sealed evidence metadata. F5 ledger
verification remains explicitly unavailable; a stored digest is not an audit seal.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.core.config import get_settings
from app.features.registration.schemas import BuyerEvidenceSummary
from app.features.registration.service import buyer_evidence_summaries
from app.features.registry.models import (
    RegistryCredit,
    RegistryCreditEvent,
    RegistryEvidence,
    RegistryProjectAccess,
)
from app.features.registry.schemas import CreditPage, EvidenceOut, PublicationIn


def _staff(actor: User) -> None:
    if not actor.is_active or actor.role not in (Role.REGISTRY_STAFF, Role.ADMIN):
        raise HTTPException(403, "Registry staff access required")


def snapshot_digest(credit: RegistryCredit) -> str:
    data = PublicationIn.model_validate(credit, from_attributes=True).model_dump(mode="json")
    # Normalize timestamps so offsets and PostgreSQL UTC conversion hash identically.
    for field in ("signed_off_at", "issued_at"):
        data[field] = getattr(credit, field).astimezone(UTC).isoformat()
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def publish_credit(
    db: Session, *, data: PublicationIn, developer: User, actor: User
) -> RegistryCredit:
    """Persist an already-approved public snapshot in the caller's transaction.

    F3's issuance service validates the real approval, supplies the batch values
    and links this row to the source project/approval before committing. The demo
    command also uses this low-level handoff; it marks synthetic rows explicitly.
    Serial allocation belongs to F3, not to registry read endpoints.
    """
    _staff(actor)
    if developer.role != Role.DEVELOPER or developer.id == actor.id:
        raise HTTPException(403, "Publication requires an independent project developer")
    if data.signed_off_at.utcoffset() is None or data.issued_at.utcoffset() is None:
        raise HTTPException(422, "Publication dates must include a timezone")
    if data.signed_off_at > data.issued_at or data.issued_at > datetime.now(UTC):
        raise HTTPException(422, "Sign-off must precede issuance; issuance cannot be in the future")
    credit = RegistryCredit(
        **data.model_dump(), developer_id=developer.id, published_by_id=actor.id, status="active"
    )
    credit.snapshot_sha256 = snapshot_digest(credit)
    try:
        with db.begin_nested():
            db.add(credit)
            db.flush()
            db.add(
                RegistryCreditEvent(
                    credit_id=credit.id, action="issued", occurred_at=data.issued_at
                )
            )
            db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            409, "Credit serial already published or publication is invalid"
        ) from exc
    return credit


def change_status(
    db: Session, credit_id: int, *, status: Literal["retired", "revoked"], actor: User
) -> RegistryCredit:
    """Trusted lifecycle handoff; history and status change atomically in caller transaction."""
    _staff(actor)
    if status not in ("retired", "revoked"):
        raise HTTPException(422, "Unsupported credit status")
    credit = db.scalar(
        select(RegistryCredit)
        .where(RegistryCredit.id == credit_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if credit is None:
        raise HTTPException(404, "Credit not found")
    if credit.status != "active":
        raise HTTPException(409, "Credit already retired or revoked")
    credit.status = status
    db.add(RegistryCreditEvent(credit_id=credit.id, action=status, occurred_at=datetime.now(UTC)))
    db.flush()
    return credit


def _buyer_projects(user: User) -> Select[tuple[str]]:
    return select(RegistryProjectAccess.project_reference).where(
        RegistryProjectAccess.buyer_id == user.id
    )


def _visible_credits() -> Select[tuple[RegistryCredit]]:
    stmt = select(RegistryCredit)
    settings = get_settings()
    if settings.app_env != "development" or not settings.seed_demo_users:
        stmt = stmt.where(RegistryCredit.is_demo.is_(False))
    return stmt


def list_credits(
    db: Session, *, user: User | None, q: str, page: int, page_size: int
) -> CreditPage:
    stmt = _visible_credits()
    if user and user.role == Role.BUYER:
        stmt = stmt.where(RegistryCredit.project_reference.in_(_buyer_projects(user)))
    if term := q.strip():
        stmt = stmt.where(
            or_(
                RegistryCredit.project_name.icontains(term, autoescape=True),
                RegistryCredit.serial.icontains(term, autoescape=True),
                RegistryCredit.country.icontains(term, autoescape=True),
                RegistryCredit.project_reference.icontains(term, autoescape=True),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(RegistryCredit.vintage.desc(), RegistryCredit.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return CreditPage(items=items, total=total, page=page, page_size=page_size)


def get_credit(db: Session, credit_id: int, user: User | None) -> RegistryCredit:
    stmt = _visible_credits().where(RegistryCredit.id == credit_id)
    if user and user.role == Role.BUYER:
        stmt = stmt.where(RegistryCredit.project_reference.in_(_buyer_projects(user)))
    credit = db.scalar(stmt)
    if credit is None:
        raise HTTPException(404, "Credit not found")
    return credit


def evidence_pack(
    db: Session, credit_id: int, user: User
) -> tuple[RegistryCredit, list[BuyerEvidenceSummary | EvidenceOut]]:
    # Authorize the credit before even asking F1 for the project's safe metadata.
    if not user.is_active or user.role not in (Role.BUYER, Role.REGISTRY_STAFF, Role.ADMIN):
        raise HTTPException(403, "Buyer or registry staff access required")
    credit = get_credit(db, credit_id, user)
    if credit.is_demo:
        items = db.scalars(
            select(RegistryEvidence)
            .where(
                RegistryEvidence.credit_id == credit.id, RegistryEvidence.buyer_visible.is_(True)
            )
            .order_by(RegistryEvidence.id)
        )
        return credit, [EvidenceOut.model_validate(item) for item in items]
    if credit.source_project_id is None:
        return (
            credit,
            [],
        )  # Legacy unlinked publications must never borrow a guessed project's files.
    return credit, list(buyer_evidence_summaries(db, credit.source_project_id))
