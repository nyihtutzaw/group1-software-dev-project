"""Reset the demo database from the admin's System › Demo data page.

Only where demo accounts exist (development, or the hosted class demo with DEMO_MODE=true): on a
real registry the API refuses and the page says so. A reset empties every table in one statement
(the schema and migrations are kept) and loads one of two starting points:

- `live`: the six demo accounts plus one neighbouring project, Huai Nam Rin Community Forest, with
  its boundary. This is where the live demo and the team's demo video start: the presenters
  register Nam Wa from scratch, and its first-survey boundary overlaps the neighbour (F2).
- `full`: the sample data testers see after a deploy (projects, boundaries, assignments and the
  synthetic registry credits), the same as `python -m app.seed` plus the registry demo.

TRUNCATE skips the row-level "append-only" triggers on the ledger and the evidence tables, which
is why this lives behind demo mode and the admin role. The new ledger starts with a
`demo_data.reset` entry, so the reset itself is on the record. Evidence files already in storage
are left alone (they are write-once), as the GitHub "Reset demo data" action does.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.config import get_settings
from app.core.db import Base, get_db
from app.core.models_registry import import_all_models
from app.features.audit.ledger import record_action
from app.features.audit.models import LedgerEntry
from app.features.boundary.models import Boundary, BoundarySource
from app.features.registration.models import Project
from app.features.registry.models import RegistryCredit

# `project_code_seq` is not owned by a column, so TRUNCATE ... RESTART IDENTITY leaves it alone.
PROJECT_CODE_START = 200


class DemoStart(StrEnum):
    LIVE = "live"
    FULL = "full"


# The live demo's neighbour. Same shape as frontend/public/tutorials/samples/
# sample-neighbour-boundary.geojson (494.9 ha), 162 m east of Nam Wa's final boundary
# (sample-boundary.geojson); Nam Wa's first survey (sample-boundary-draft.geojson) overlaps it by
# 17.5 ha, 4.6% of its own area, above the 0.5% tolerance.
NEIGHBOUR = {
    "code": "CRVR-0174",
    "name": "Huai Nam Rin Community Forest",
    "owner": "developer2@crvr.local",
    "methodology": "VM0047",
    "crediting_start_year": 2025,
    "crediting_end_year": 2045,
    "area_ha": 495,
    "est_removal_tco2e": 38000,
    "baseline_summary": (
        "Degraded community forest after repeated dry-season fires; 14 tC/ha in 2025."
    ),
    "additionality_reasoning": (
        "Fire breaks, patrols and replanting cost more than the village earns from the land; no "
        "rule requires them and no grant covers them."
    ),
    "submitted": datetime(2026, 10, 20, 9, 30, tzinfo=UTC),
}
NEIGHBOUR_BOUNDARY = {
    "type": "Polygon",
    "coordinates": [
        [
            [100.8775, 18.8005],
            [100.8765, 18.7885],
            [100.8835, 18.7825],
            [100.8985, 18.784],
            [100.901, 18.799],
            [100.889, 18.805],
            [100.8775, 18.8005],
        ]
    ],
}


def _require_demo_mode() -> None:
    if not get_settings().demo_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Demo data can only be reset on a demo server"
        )


def wipe_all_tables(db: Session) -> None:
    """Empty every application table and restart its ids. Waits at most 10 s for other requests."""
    import_all_models()
    names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    db.execute(text("SET LOCAL lock_timeout = '10s'"))
    db.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    db.execute(text(f"ALTER SEQUENCE project_code_seq RESTART WITH {PROJECT_CODE_START}"))
    # The identity map still holds rows that no longer exist (the signed-in admin, for one).
    db.expunge_all()


def seed_live_start(db: Session) -> None:
    """The neighbouring project and its boundary (the accounts are already there)."""
    from app.features.boundary import service as boundary_service

    owner = db.scalar(select(User).where(User.email == NEIGHBOUR["owner"]))
    if owner is None:
        raise RuntimeError(f"{NEIGHBOUR['owner']} is missing from the demo accounts")
    fields = {k: v for k, v in NEIGHBOUR.items() if k not in ("owner", "submitted")}
    project = Project(
        **fields,
        owner_id=owner.id,
        status="submitted",
        created_at=NEIGHBOUR["submitted"],
        submitted_at=NEIGHBOUR["submitted"],
    )
    db.add(project)
    db.flush()
    boundary_service.save_boundary(db, project, NEIGHBOUR_BOUNDARY, BoundarySource.UPLOADED, owner)


def reset_demo_data(db: Session, start: DemoStart, requested_by: str) -> None:
    """Wipe everything and load `start`. The seeders commit as they go."""
    from app.features.registry.demo import seed_registry_demo
    from app.seed import seed_demo_data, seed_demo_users

    wipe_all_tables(db)
    seed_demo_users(db)
    actor = db.scalar(select(User).where(User.email == requested_by))
    record_action(
        db,
        actor=actor,
        action="demo_data.reset",
        entity="system",
        entity_id=0,
        payload={"start": start.value, "requested_by": requested_by},
    )
    db.commit()
    if start is DemoStart.LIVE:
        seed_live_start(db)
    else:
        seed_demo_data(db)
        seed_registry_demo(db)
    db.commit()


def demo_data_counts(db: Session) -> dict[str, int]:
    def count(model: Any) -> int:
        return db.scalar(select(func.count()).select_from(model)) or 0

    return {
        "users": count(User),
        "projects": count(Project),
        "boundaries": count(Boundary),
        "credits": count(RegistryCredit),
        "ledger_entries": count(LedgerEntry),
    }


# ---- API ---------------------------------------------------------------------------------------

router = APIRouter(prefix="/admin/demo-data", tags=["F5 demo data"])


class DemoDataOut(BaseModel):
    enabled: bool
    counts: dict[str, int]


class DemoResetIn(BaseModel):
    start: DemoStart
    confirm: str


@router.get("", response_model=DemoDataOut)
def get_demo_data(
    db: Session = Depends(get_db), _user: User = Depends(require_roles(Role.ADMIN))
) -> DemoDataOut:
    """Whether this server allows a reset, and how much data it holds now."""
    return DemoDataOut(enabled=get_settings().demo_enabled, counts=demo_data_counts(db))


@router.post("/reset", response_model=DemoDataOut)
def post_demo_reset(
    data: DemoResetIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ADMIN)),
) -> DemoDataOut:
    """Wipe all data and load the chosen starting point. The body must carry `confirm: "RESET"`."""
    _require_demo_mode()
    if data.confirm != "RESET":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, 'Type "RESET" to confirm')
    email = user.email
    try:
        reset_demo_data(db, data.start, requested_by=email)
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "The database is busy. Try the reset again in a moment."
        ) from exc
    return DemoDataOut(enabled=True, counts=demo_data_counts(db))
