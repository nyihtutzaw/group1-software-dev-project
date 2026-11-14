import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.auth.models import Role
from app.features.audit.ledger import (
    GENESIS_PREV_HASH,
    canonical_json,
    compute_hash,
    entry_to_canonical_dict,
    record_action,
    verify_ledger_chain,
)
from app.features.audit.models import LedgerEntry


def test_canonical_json_deterministic():
    """Key ordering and whitespace in payloads must not change the resulting hash."""
    d1 = {"z": 10, "a": "hello", "m": [1, 2, 3]}
    d2 = {"a": "hello", "m": [1, 2, 3], "z": 10}

    assert canonical_json(d1) == canonical_json(d2)
    assert compute_hash(GENESIS_PREV_HASH, d1) == compute_hash(GENESIS_PREV_HASH, d2)


def test_record_action_creates_hash_chained_entries(db, make_user):
    """record_action() inserts into the caller transaction with SHA-256 hash chaining."""
    user = make_user(Role.DEVELOPER, email="dev@example.com")

    # First entry: genesis
    e1 = record_action(
        db,
        actor=user,
        action="project.created",
        entity="project",
        entity_id=101,
        payload={"name": "Mangrove Restoration"},
    )

    assert e1.id is not None
    assert e1.prev_hash == GENESIS_PREV_HASH
    assert e1.actor_id == user.id
    assert e1.actor_email == "dev@example.com"
    assert e1.entity == "project"
    assert e1.entity_id == 101
    assert e1.payload == {"name": "Mangrove Restoration"}
    assert e1.hash == compute_hash(GENESIS_PREV_HASH, entry_to_canonical_dict(e1))

    # Second entry: system action (actor=None)
    e2 = record_action(
        db,
        actor=None,
        action="boundary.overlap_checked",
        entity="boundary",
        entity_id=202,
        payload={"overlap_pct": 0.0},
    )

    assert e2.id is not None
    assert e2.prev_hash == e1.hash
    assert e2.actor_id is None
    assert e2.actor_email is None
    assert e2.hash == compute_hash(e1.hash, entry_to_canonical_dict(e2))

    # Third entry
    e3 = record_action(
        db,
        actor=user,
        action="evidence.uploaded",
        entity="evidence_file",
        entity_id=303,
        payload={"filename": "survey.pdf", "size_bytes": 1024},
    )

    assert e3.prev_hash == e2.hash

    valid, err = verify_ledger_chain(db)
    assert valid is True
    assert err is None


def test_ledger_detects_tampered_payload(db, make_user):
    """Modifying a payload breaks cryptographic hash verification."""
    user = make_user(Role.DEVELOPER)

    record_action(db, actor=user, action="action.one", entity="project", entity_id=1)
    e2 = record_action(db, actor=user, action="action.two", entity="project", entity_id=2)
    record_action(db, actor=user, action="action.three", entity="project", entity_id=3)

    assert verify_ledger_chain(db)[0] is True

    # Temporarily disable the write-once trigger in this transaction
    # to simulate unauthorized DB tampering
    db.execute(text("ALTER TABLE ledger_entries DISABLE TRIGGER ledger_entries_no_update_delete"))
    db.execute(
        text("UPDATE ledger_entries SET payload = :tampered WHERE id = :id"),
        {"tampered": '{"fraudulent": true}', "id": e2.id},
    )
    db.execute(text("ALTER TABLE ledger_entries ENABLE TRIGGER ledger_entries_no_update_delete"))

    # Evict cache so SQLAlchemy reads the altered row from DB
    db.expire_all()

    valid, err = verify_ledger_chain(db)
    assert valid is False
    assert f"Hash mismatch at entry id={e2.id}" in err


def test_ledger_detects_tampered_prev_hash(db, make_user):
    """Altering prev_hash breaks the hash chain link."""
    user = make_user(Role.DEVELOPER)

    record_action(db, actor=user, action="action.one", entity="project", entity_id=1)
    e2 = record_action(db, actor=user, action="action.two", entity="project", entity_id=2)

    db.execute(text("ALTER TABLE ledger_entries DISABLE TRIGGER ledger_entries_no_update_delete"))
    db.execute(
        text("UPDATE ledger_entries SET prev_hash = :fake_hash WHERE id = :id"),
        {"fake_hash": "a" * 64, "id": e2.id},
    )
    db.execute(text("ALTER TABLE ledger_entries ENABLE TRIGGER ledger_entries_no_update_delete"))

    db.expire_all()

    valid, err = verify_ledger_chain(db)
    assert valid is False
    assert f"Broken prev_hash chain at entry id={e2.id}" in err


def test_ledger_detects_deleted_entry(db, make_user):
    """Removing an entry creates an unlinked gap in prev_hash."""
    user = make_user(Role.DEVELOPER)

    record_action(db, actor=user, action="action.one", entity="project", entity_id=1)
    e2 = record_action(db, actor=user, action="action.two", entity="project", entity_id=2)
    e3 = record_action(db, actor=user, action="action.three", entity="project", entity_id=3)

    db.execute(text("ALTER TABLE ledger_entries DISABLE TRIGGER ledger_entries_no_update_delete"))
    db.execute(text("DELETE FROM ledger_entries WHERE id = :id"), {"id": e2.id})
    db.execute(text("ALTER TABLE ledger_entries ENABLE TRIGGER ledger_entries_no_update_delete"))

    db.expire_all()

    valid, err = verify_ledger_chain(db)
    assert valid is False
    assert f"Broken prev_hash chain at entry id={e3.id}" in err


def test_ledger_entries_cannot_be_updated_at_db_level(db, make_user):
    """DB trigger prevents any UPDATE operation on ledger_entries."""
    user = make_user(Role.DEVELOPER)
    entry = record_action(db, actor=user, action="action.test", entity="project", entity_id=1)

    with pytest.raises(DBAPIError, match="ledger_entries is append-only"):
        db.execute(
            text("UPDATE ledger_entries SET action = 'tampered' WHERE id = :id"),
            {"id": entry.id},
        )


def test_ledger_entries_cannot_be_deleted_at_db_level(db, make_user):
    """DB trigger prevents any DELETE operation on ledger_entries."""
    user = make_user(Role.DEVELOPER)
    entry = record_action(db, actor=user, action="action.test", entity="project", entity_id=1)

    with pytest.raises(DBAPIError, match="ledger_entries is append-only"):
        db.execute(
            text("DELETE FROM ledger_entries WHERE id = :id"),
            {"id": entry.id},
        )


def test_record_action_rolls_back_with_caller_transaction(db, make_user):
    """If the caller's transaction rolls back, the ledger entry is also rolled back."""
    user = make_user(Role.DEVELOPER)

    savepoint = db.begin_nested()
    record_action(db, actor=user, action="temporary.action", entity="project", entity_id=999)
    savepoint.rollback()

    entries = db.scalars(select(LedgerEntry).where(LedgerEntry.action == "temporary.action")).all()
    assert len(entries) == 0


def test_ledger_api_endpoints_and_rbac(client, login, db, make_user):
    """Ledger endpoints enforce RBAC and return serialized hash-chained entries."""
    user = make_user(Role.DEVELOPER, email="p@test.local")
    record_action(
        db,
        actor=user,
        action="project.submitted",
        entity="project",
        entity_id=42,
        payload={"credits": 500},
    )

    # Developers cannot access the audit ledger
    login(Role.DEVELOPER)
    assert client.get("/api/ledger").status_code == 403
    assert client.get("/api/ledger/verify").status_code == 403

    # Buyers can view the ledger but not trigger verify
    login(Role.BUYER)
    res = client.get("/api/ledger")
    assert res.status_code == 200
    entries = res.json()
    assert len(entries) >= 1
    assert entries[0]["action"] == "project.submitted"
    assert entries[0]["entity"] == "project"
    assert entries[0]["entity_id"] == 42
    assert "hash" in entries[0]
    assert "prev_hash" in entries[0]
    assert client.get("/api/ledger/verify").status_code == 403

    # Registry staff can view and verify
    login(Role.REGISTRY_STAFF)
    assert client.get("/api/ledger").status_code == 200
    verify_res = client.get("/api/ledger/verify")
    assert verify_res.status_code == 200
    assert verify_res.json() == {"valid": True, "error": None}
