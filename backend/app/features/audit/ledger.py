"""F5 audit ledger — tamper-evident, append-only, hash-chained activity log (FR-07, FR-09).

Every critical action across CRVR (project submission, boundary changes, verification decisions,
approvals, credit issuance) must be recorded here. Each entry seals the cryptographic hash
of the previous entry, so any alteration breaks the chain.
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.features.audit.models import LedgerEntry

log = logging.getLogger("crvr.ledger")

GENESIS_PREV_HASH: str = "0" * 64
LEDGER_LOCK_KEY: int = 847291


def format_timestamp(dt: datetime) -> str:
    """Deterministic UTC timestamp with microsecond resolution."""
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonical_json(data: Any) -> str:
    """Canonical JSON serialization: sorted keys, compact separators, deterministic encoding."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def entry_to_canonical_dict(entry: LedgerEntry) -> dict[str, Any]:
    """Convert an existing LedgerEntry into its canonical dictionary for hash verification."""
    return {
        "action": entry.action,
        "actor_email": entry.actor_email,
        "actor_id": entry.actor_id,
        "created_at": format_timestamp(entry.created_at),
        "entity": entry.entity,
        "entity_id": entry.entity_id,
        "payload": entry.payload or {},
    }


def compute_hash(prev_hash: str, entry_dict: dict[str, Any]) -> str:
    """Compute sha256(prev_hash || canonical_json(entry))."""
    serialized = prev_hash + canonical_json(entry_dict)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def record_action(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity: str,
    entity_id: int,
    payload: dict[str, Any] | None = None,
) -> LedgerEntry:
    """Record a critical action into the append-only, hash-chained ledger.

    Inserts in the caller's transaction, before commit.
    """
    # 1. Take a transaction-level advisory lock so concurrent writers serialize hash computation
    db.execute(text(f"SELECT pg_advisory_xact_lock({LEDGER_LOCK_KEY})"))

    # 2. Get the hash of the latest ledger entry
    latest_stmt = select(LedgerEntry).order_by(LedgerEntry.id.desc()).limit(1)
    latest_entry = db.scalar(latest_stmt)
    prev_hash = latest_entry.hash if latest_entry else GENESIS_PREV_HASH

    # 3. Form entry and compute sha256(prev_hash || canonical_json(entry))
    now = datetime.now(UTC)
    actor_id = actor.id if actor else None
    actor_email = actor.email if actor else None
    payload_data = payload or {}

    entry_data = {
        "action": action,
        "actor_email": actor_email,
        "actor_id": actor_id,
        "created_at": format_timestamp(now),
        "entity": entity,
        "entity_id": entity_id,
        "payload": payload_data,
    }
    entry_hash = compute_hash(prev_hash, entry_data)

    # 4. Insert into ledger_entries and flush to assign sequence ID
    entry = LedgerEntry(
        created_at=now,
        action=action,
        actor_id=actor_id,
        actor_email=actor_email,
        entity=entity,
        entity_id=entity_id,
        payload=payload_data,
        prev_hash=prev_hash,
        hash=entry_hash,
    )
    db.add(entry)
    db.flush()

    log.info(
        "ledger #%d %s %s#%s by %s hash=%s",
        entry.id,
        action,
        entity,
        entity_id,
        actor_email or "system",
        entry_hash[:8],
    )
    return entry


def verify_ledger_chain(db: Session) -> tuple[bool, str | None]:
    """Walk the ledger from beginning to end and verify the cryptographic hash chain.

    Returns (True, None) if the chain is intact.
    Returns (False, error_description) if any entry was altered, removed, or out of order.
    """
    entries = db.scalars(select(LedgerEntry).order_by(LedgerEntry.id.asc())).all()
    expected_prev_hash = GENESIS_PREV_HASH

    for entry in entries:
        if entry.prev_hash != expected_prev_hash:
            return False, (
                f"Broken prev_hash chain at entry id={entry.id}: "
                f"expected {expected_prev_hash}, found {entry.prev_hash}"
            )

        expected_hash = compute_hash(entry.prev_hash, entry_to_canonical_dict(entry))
        if entry.hash != expected_hash:
            return False, (
                f"Hash mismatch at entry id={entry.id}: "
                f"expected {expected_hash}, stored {entry.hash}"
            )

        expected_prev_hash = entry.hash

    return True, None
