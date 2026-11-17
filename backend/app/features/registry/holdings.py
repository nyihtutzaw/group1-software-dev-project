"""Credit holdings and buyer retirement (#44): schemas, service and routes in one module.

Registry staff allocate a contiguous unit range of an issued batch to a buyer (the registry's
record of a sale). The buyer retires all or part of a held range to claim an offset, giving a
beneficiary, reason and reporting year. Partial retirement splits the range; retired rows are
locked by a database trigger, so they can never be transferred, resold or unretired. When every
unit of a batch is retired, the batch status becomes ``retired``. Each allocation and retirement
is sealed in the F5 ledger. Retirement records (not buyer identities) are public.

Buffer credits (#42) do not exist yet; when they do, they must be refused here.
"""

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.db import get_db
from app.features.audit.ledger import record_action
from app.features.registry.models import (
    RegistryCredit,
    RegistryCreditEvent,
    RegistryHolding,
    RegistryProjectAccess,
)
from app.features.registry.service import _visible_credits, get_credit

STAFF = (Role.REGISTRY_STAFF, Role.ADMIN)


# --- Schemas ---------------------------------------------------------------------------------


class AllocationIn(BaseModel):
    # Plain string, not EmailStr: demo and test accounts use the reserved .local domain.
    # The value is only looked up against existing buyer accounts, never stored.
    model_config = ConfigDict(str_strip_whitespace=True)
    buyer_email: str = Field(min_length=3, max_length=255)
    quantity: int = Field(gt=0)


class RetirementIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    quantity: int = Field(gt=0)
    beneficiary: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=500)
    reporting_year: int = Field(ge=1900, le=2200)


class HoldingOut(BaseModel):
    id: int
    serial_block: str
    first_unit: int
    last_unit: int
    quantity: int
    status: str
    allocated_at: datetime
    retired_at: datetime | None
    beneficiary: str | None
    reason: str | None
    reporting_year: int | None
    # Only registry staff see whose holding it is; buyers only ever receive their own.
    buyer_email: str | None = None


class HoldingsOut(BaseModel):
    quantity: int
    allocated: int
    unallocated: int
    retired: int
    items: list[HoldingOut]


class RetirementOut(BaseModel):
    serial_block: str
    quantity: int
    beneficiary: str
    reason: str
    reporting_year: int
    retired_at: datetime


class RetirementsOut(BaseModel):
    quantity: int
    retired_quantity: int
    items: list[RetirementOut]


class RetireResultOut(BaseModel):
    retired: HoldingOut
    remaining: HoldingOut | None


# --- Service ---------------------------------------------------------------------------------

_SERIAL_RANGE = re.compile(r"^(?P<prefix>.*)-(?P<first>\d+)-(?P<last>\d+)$")


def serial_block(credit: RegistryCredit, first: int, last: int) -> str:
    """Unit-range serial within a batch, e.g. ``…-000000001-000000500`` from ``…-1-8400``."""
    match = _SERIAL_RANGE.match(credit.serial)
    if not match:
        return f"{credit.serial} #{first}–{last}"
    width_first, width_last = len(match["first"]), len(match["last"])
    return f"{match['prefix']}-{first:0{width_first}d}-{last:0{width_last}d}"


def _holding_out(credit: RegistryCredit, holding: RegistryHolding, email: str | None) -> HoldingOut:
    return HoldingOut(
        id=holding.id,
        serial_block=serial_block(credit, holding.first_unit, holding.last_unit),
        first_unit=holding.first_unit,
        last_unit=holding.last_unit,
        quantity=holding.quantity,
        status=holding.status,
        allocated_at=holding.allocated_at,
        retired_at=holding.retired_at,
        beneficiary=holding.beneficiary,
        reason=holding.reason,
        reporting_year=holding.reporting_year,
        buyer_email=email,
    )


def _holdings(db: Session, credit_id: int) -> list[RegistryHolding]:
    return list(
        db.scalars(
            select(RegistryHolding)
            .where(RegistryHolding.credit_id == credit_id)
            .order_by(RegistryHolding.first_unit)
        )
    )


def _lock_credit(db: Session, credit_id: int) -> RegistryCredit:
    credit = db.scalar(
        _visible_credits()
        .where(RegistryCredit.id == credit_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if credit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Credit not found")
    return credit


def allocated_units(db: Session, credit_id: int) -> int:
    return db.scalar(
        select(func.coalesce(func.max(RegistryHolding.last_unit), 0)).where(
            RegistryHolding.credit_id == credit_id
        )
    )


def list_holdings(db: Session, credit_id: int, user: User) -> HoldingsOut:
    credit = get_credit(db, credit_id, user)  # buyer grants apply, as on every registry read
    holdings = _holdings(db, credit.id)
    allocated = sum(holding.quantity for holding in holdings)
    retired = sum(holding.quantity for holding in holdings if holding.status == "retired")
    if user.role == Role.BUYER:
        items = [_holding_out(credit, h, None) for h in holdings if h.buyer_id == user.id]
    else:
        emails = dict(
            db.execute(
                select(User.id, User.email).where(User.id.in_({h.buyer_id for h in holdings}))
            ).all()
        )
        items = [_holding_out(credit, h, emails.get(h.buyer_id)) for h in holdings]
    return HoldingsOut(
        quantity=credit.quantity,
        allocated=allocated,
        unallocated=credit.quantity - allocated,
        retired=retired,
        items=items,
    )


def allocate(db: Session, credit_id: int, actor: User, data: AllocationIn) -> HoldingOut:
    if not actor.is_active or actor.role not in STAFF:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Registry staff access required")
    credit = _lock_credit(db, credit_id)  # serialises allocations of this batch
    if credit.status != "active":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A {credit.status} batch cannot be allocated"
        )
    buyer = db.scalar(select(User).where(func.lower(User.email) == data.buyer_email.lower()))
    if buyer is None or buyer.role != Role.BUYER or not buyer.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active buyer account")
    has_access = db.scalar(
        select(RegistryProjectAccess.buyer_id).where(
            RegistryProjectAccess.project_reference == credit.project_reference,
            RegistryProjectAccess.buyer_id == buyer.id,
        )
    )
    if has_access is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Grant the buyer access to this project before allocating"
        )
    first = allocated_units(db, credit.id) + 1
    remaining = credit.quantity - first + 1
    if data.quantity > remaining:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Only {remaining} unallocated credits remain in this batch",
        )
    holding = RegistryHolding(
        credit_id=credit.id,
        buyer_id=buyer.id,
        first_unit=first,
        last_unit=first + data.quantity - 1,
        status="held",
        allocated_at=datetime.now(UTC),
        allocated_by_id=actor.id,
    )
    db.add(holding)
    db.flush()
    record_action(
        db,
        actor=actor,
        action="credit.allocated",
        entity="credit",
        entity_id=credit.id,
        payload={
            "credit_id": credit.id,
            "holding_id": holding.id,
            "buyer_id": buyer.id,
            "first_unit": holding.first_unit,
            "last_unit": holding.last_unit,
            "quantity": holding.quantity,
        },
    )
    db.commit()
    return _holding_out(credit, holding, buyer.email)


def retire(db: Session, holding_id: int, actor: User, data: RetirementIn) -> RetireResultOut:
    if not actor.is_active or actor.role != Role.BUYER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the buyer holding credits can retire")
    found = db.scalar(select(RegistryHolding).where(RegistryHolding.id == holding_id))
    if found is None or found.buyer_id != actor.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Holding not found")
    # Lock order: batch, then holding — the same order as allocation, so no deadlock.
    credit = _lock_credit(db, found.credit_id)
    holding = db.scalar(
        select(RegistryHolding)
        .where(RegistryHolding.id == holding_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if holding.status != "held":
        raise HTTPException(status.HTTP_409_CONFLICT, "These credits are already retired")
    if credit.status != "active":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Credits in a {credit.status} batch cannot be retired"
        )
    if data.quantity > holding.quantity:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"You hold {holding.quantity} credits in this range",
        )
    if data.reporting_year > datetime.now(UTC).year:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "The reporting year cannot be in the future"
        )

    now = datetime.now(UTC)
    remaining = None
    if data.quantity < holding.quantity:
        # Split: the retired part keeps this row; the rest stays held in a new row.
        remaining = RegistryHolding(
            credit_id=holding.credit_id,
            buyer_id=holding.buyer_id,
            first_unit=holding.first_unit + data.quantity,
            last_unit=holding.last_unit,
            status="held",
            allocated_at=holding.allocated_at,
            allocated_by_id=holding.allocated_by_id,
        )
        holding.last_unit = holding.first_unit + data.quantity - 1
    holding.status = "retired"
    holding.retired_at = now
    holding.beneficiary = data.beneficiary
    holding.reason = data.reason
    holding.reporting_year = data.reporting_year
    db.flush()
    if remaining is not None:
        db.add(remaining)
        db.flush()

    record_action(
        db,
        actor=actor,
        action="credit.retired",
        entity="credit",
        entity_id=credit.id,
        payload={
            "credit_id": credit.id,
            "holding_id": holding.id,
            "first_unit": holding.first_unit,
            "last_unit": holding.last_unit,
            "quantity": holding.quantity,
            "beneficiary": holding.beneficiary,
            "reason": holding.reason,
            "reporting_year": holding.reporting_year,
        },
    )
    retired_total = db.scalar(
        select(
            func.coalesce(func.sum(RegistryHolding.last_unit - RegistryHolding.first_unit + 1), 0)
        ).where(RegistryHolding.credit_id == credit.id, RegistryHolding.status == "retired")
    )
    if retired_total == credit.quantity:
        credit.status = "retired"
        db.add(RegistryCreditEvent(credit_id=credit.id, action="retired", occurred_at=now))
        db.flush()
    db.commit()
    return RetireResultOut(
        retired=_holding_out(credit, holding, None),
        remaining=_holding_out(credit, remaining, None) if remaining else None,
    )


def retirements(db: Session, credit_id: int, user: User | None) -> RetirementsOut:
    credit = get_credit(db, credit_id, user)
    items = [
        RetirementOut(
            serial_block=serial_block(credit, h.first_unit, h.last_unit),
            quantity=h.quantity,
            beneficiary=h.beneficiary,
            reason=h.reason,
            reporting_year=h.reporting_year,
            retired_at=h.retired_at,
        )
        for h in _holdings(db, credit.id)
        if h.status == "retired"
    ]
    return RetirementsOut(
        quantity=credit.quantity,
        retired_quantity=sum(item.quantity for item in items),
        items=items,
    )


# --- Routes (mounted under /registry; public retirements route is in router.py) --------------

router = APIRouter(tags=["F4 registry"])


@router.get("/credits/{credit_id}/holdings", response_model=HoldingsOut)
def get_holdings(
    credit_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.BUYER, *STAFF)),
) -> HoldingsOut:
    return list_holdings(db, credit_id, user)


@router.post(
    "/credits/{credit_id}/holdings",
    response_model=HoldingOut,
    status_code=status.HTTP_201_CREATED,
)
def post_allocation(
    credit_id: int,
    body: AllocationIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*STAFF)),
) -> HoldingOut:
    return allocate(db, credit_id, user, body)


@router.post("/holdings/{holding_id}/retire", response_model=RetireResultOut)
def post_retirement(
    holding_id: int,
    body: RetirementIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.BUYER)),
) -> RetireResultOut:
    return retire(db, holding_id, user, body)
