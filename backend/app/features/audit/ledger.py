"""F5 audit ledger — the single entry point other features use to record critical actions.

STUB added by F2 so features can call it from day one. F5 (Put) replaces the body with the
hash-chained `ledger_entries` insert; the signature should stay the same so callers don't change.

    record_action(db, actor=user, action="boundary.saved", entity="project", entity_id=p.id,
                  payload={"area_m2": 12_400_000})

`actor=None` means the system (e.g. an automatic check). Call it inside the same transaction
as the change it describes, before `db.commit()`.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.auth.models import User

log = logging.getLogger("crvr.ledger")


def record_action(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity: str,
    entity_id: int,
    payload: dict[str, Any] | None = None,
) -> None:
    """Record a critical action. Stub: logs only until F5 implements the ledger table."""
    log.info(
        "ledger %s %s#%s by %s %s",
        action,
        entity,
        entity_id,
        actor.email if actor else "system",
        payload or {},
    )
