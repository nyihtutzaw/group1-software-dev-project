"""F1 crypto-erasure — one test (or more) per acceptance criterion of change request #45.

The landowner's case: a sealed land-title scan shows a national ID number. Destroying the
file is impossible by design, so the key is destroyed instead. These tests check that the
content really is unreadable afterwards, and that everything which must survive does.
"""

import hashlib

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.auth.models import Role
from app.core.config import get_settings
from app.features.registration.crypto import EvidenceUndecryptableError, decrypt, encrypt, new_key
from app.features.registration.models import (
    EvidenceErasure,
    EvidenceFile,
    EvidenceKey,
)

PDF = b"%PDF-1.7 land title, national ID 1-2345-67890-12-3, 42 Moo 4, Nan"
REDACTED = b"%PDF-1.7 land title, national ID [redacted], address [redacted]"


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
def sealed(client, login):
    """A developer's draft with one sealed land title holding personal data."""
    login(Role.DEVELOPER)
    project = client.post("/api/projects", json={"name": "Nan land parcel"}).json()
    evidence = client.post(
        f"/api/projects/{project['id']}/evidence",
        files={"file": ("title.pdf", PDF, "application/pdf")},
        data={"kind": "land_title"},
    ).json()
    return project, evidence


def _erase(client, project, evidence_id, **body):
    payload = {"reason": "Data protection request from the landowner", **body}
    return client.post(
        f"/api/projects/{project['id']}/evidence/{evidence_id}/erasure", json=payload
    )


def _download(client, project, evidence_id):
    return client.get(f"/api/projects/{project['id']}/evidence/{evidence_id}/file")


# --- the cipher itself -------------------------------------------------------------------


def test_a_file_is_unreadable_without_its_key():
    key = new_key()
    nonce, ciphertext = encrypt(PDF, key)

    assert PDF not in ciphertext
    assert decrypt(ciphertext, key, nonce) == PDF
    with pytest.raises(EvidenceUndecryptableError):
        decrypt(ciphertext, new_key(), nonce)


def test_every_file_gets_its_own_key():
    assert new_key() != new_key()


def test_tampering_with_the_ciphertext_is_detected():
    key = new_key()
    nonce, ciphertext = encrypt(PDF, key)
    altered = bytearray(ciphertext)
    altered[0] ^= 0xFF

    with pytest.raises(EvidenceUndecryptableError):
        decrypt(bytes(altered), key, nonce)


# --- evidence is encrypted at rest ---------------------------------------------------------


def test_the_sealed_object_holds_ciphertext_not_the_document(client, db, sealed, storage):
    project, evidence = sealed

    stored = db.get(EvidenceFile, evidence["id"])
    on_disk = (storage / stored.storage_key).read_bytes()

    assert PDF not in on_disk
    assert b"national ID" not in on_disk
    # The row still describes the plaintext, so the seal is still checkable
    assert stored.sha256 == hashlib.sha256(PDF).hexdigest()
    assert db.get(EvidenceKey, evidence["id"]) is not None


def test_the_owner_still_downloads_the_original(client, sealed):
    project, evidence = sealed

    assert _download(client, project, evidence["id"]).content == PDF


# --- erasing ------------------------------------------------------------------------------


def test_admin_erases_the_content_and_it_cannot_be_read_again(client, db, login, sealed, storage):
    project, evidence = sealed
    stored_key = db.get(EvidenceFile, evidence["id"]).storage_key
    login(Role.ADMIN)

    res = _erase(client, project, evidence["id"])

    assert res.status_code == 201, res.text
    db.expire_all()
    assert db.get(EvidenceKey, evidence["id"]) is None
    # The sealed object is untouched — only the key is gone
    assert (storage / stored_key).is_file()
    assert db.get(EvidenceFile, evidence["id"]) is not None

    gone = _download(client, project, evidence["id"])
    assert gone.status_code == 410
    assert "erased" in gone.json()["detail"]
    assert "landowner" in gone.json()["detail"]


def test_the_evidence_row_and_its_hash_survive_the_erasure(client, db, login, sealed):
    """What the file was, and that it hashed to this, is still provable — the bytes are not."""
    project, evidence = sealed
    login(Role.ADMIN)

    _erase(client, project, evidence["id"])

    db.expire_all()
    row = db.get(EvidenceFile, evidence["id"])
    assert row.filename == "title.pdf"
    assert row.sha256 == hashlib.sha256(PDF).hexdigest()
    assert row.sealed_at is not None


def test_a_redacted_replacement_is_recorded_and_offered(client, db, login, sealed):
    project, _ = sealed
    original = client.post(
        f"/api/projects/{project['id']}/evidence",
        files={"file": ("title-redacted.pdf", REDACTED, "application/pdf")},
        data={"kind": "land_title"},
    ).json()
    first = client.get(f"/api/projects/{project['id']}").json()["evidence"][0]["id"]
    login(Role.ADMIN)

    res = _erase(client, project, first, replacement_id=original["id"])

    assert res.status_code == 201
    assert res.json()["replacement_id"] == original["id"]
    detail = _download(client, project, first).json()["detail"]
    assert f"evidence {original['id']}" in detail
    # and the replacement still reads
    assert _download(client, project, original["id"]).content == REDACTED


def test_erasing_is_recorded_in_the_ledger(client, db, login, sealed):
    from app.features.audit.models import LedgerEntry

    project, evidence = sealed
    login(Role.ADMIN)

    _erase(client, project, evidence["id"])

    entry = db.scalars(select(LedgerEntry).where(LedgerEntry.action == "evidence.erased")).all()[-1]
    assert entry.payload["evidence_id"] == evidence["id"]
    assert entry.payload["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert "landowner" in entry.payload["reason"]


def test_the_same_file_cannot_be_erased_twice(client, login, sealed):
    project, evidence = sealed
    login(Role.ADMIN)
    assert _erase(client, project, evidence["id"]).status_code == 201

    assert _erase(client, project, evidence["id"]).status_code == 409


def test_the_owning_developer_cannot_erase(client, sealed):
    """The `sealed` fixture is already signed in as the project's developer."""
    project, evidence = sealed

    assert _erase(client, project, evidence["id"]).status_code in (403, 404)


@pytest.mark.parametrize("role", [Role.VERIFIER, Role.REGISTRY_STAFF, Role.BUYER])
def test_no_other_role_can_erase(client, login, sealed, role):
    project, evidence = sealed
    login(role)

    assert _erase(client, project, evidence["id"]).status_code in (403, 404)


def test_a_reason_is_required(client, login, sealed):
    project, evidence = sealed
    login(Role.ADMIN)

    assert _erase(client, project, evidence["id"], reason="too short").status_code == 422


def test_the_replacement_must_belong_to_the_same_project(client, login, sealed, make_project):
    project, evidence = sealed
    other = make_project()
    login(Role.ADMIN)

    res = _erase(client, project, evidence["id"], replacement_id=other.id)

    assert res.status_code == 422
    assert "same project" in res.json()["detail"]


def test_a_file_cannot_replace_itself(client, login, sealed):
    project, evidence = sealed
    login(Role.ADMIN)

    res = _erase(client, project, evidence["id"], replacement_id=evidence["id"])

    assert res.status_code == 422


# --- the erasure record is as permanent as the evidence -------------------------------------


@pytest.mark.parametrize("statement", ["update", "delete"])
def test_the_database_refuses_to_change_an_erasure_record(client, db, login, sealed, statement):
    project, evidence = sealed
    login(Role.ADMIN)
    _erase(client, project, evidence["id"])
    stmt = (
        update(EvidenceErasure).values(reason="never happened")
        if statement == "update"
        else delete(EvidenceErasure)
    )

    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.execute(stmt.where(EvidenceErasure.evidence_id == evidence["id"]))


def test_the_write_once_rule_on_evidence_rows_still_holds(client, db, login, sealed):
    """Erasure must not have opened a hole in what it was built to work around."""
    project, evidence = sealed

    with pytest.raises(DBAPIError, match="write-once"), db.begin_nested():
        db.execute(delete(EvidenceFile).where(EvidenceFile.id == evidence["id"]))


def test_erasing_one_file_leaves_the_others_readable(client, login, sealed):
    project, first = sealed
    second = client.post(
        f"/api/projects/{project['id']}/evidence",
        files={"file": ("survey.pdf", b"%PDF-1.7 survey", "application/pdf")},
        data={"kind": "other"},
    ).json()
    login(Role.ADMIN)

    _erase(client, project, first["id"])

    assert _download(client, project, first["id"]).status_code == 410
    assert _download(client, project, second["id"]).content == b"%PDF-1.7 survey"


def test_there_is_no_route_that_deletes_the_evidence_itself(client, login, sealed):
    """Erasure destroys a key. It must not have introduced a way to delete sealed evidence."""
    project, evidence = sealed
    login(Role.ADMIN)
    base = f"/api/projects/{project['id']}/evidence/{evidence['id']}"

    for method in ("put", "patch", "delete"):
        assert client.request(method, base).status_code in (404, 405)
        assert client.request(method, f"{base}/file").status_code in (404, 405)
        assert client.request(method, f"{base}/erasure").status_code in (404, 405)


def test_a_missing_key_without_an_erasure_record_is_not_reported_as_erased(
    client, db, login, sealed
):
    """A key lost by accident is a fault, not a data-protection decision — do not conflate them."""
    project, evidence = sealed
    db.execute(delete(EvidenceKey).where(EvidenceKey.evidence_id == evidence["id"]))
    db.commit()

    res = _download(client, project, evidence["id"])

    assert res.status_code == 404
    assert "key is missing" in res.json()["detail"]


def test_altered_ciphertext_is_refused_rather_than_returned(client, db, sealed, storage):
    project, evidence = sealed
    stored = db.get(EvidenceFile, evidence["id"])
    path = storage / stored.storage_key
    path.chmod(0o644)
    path.write_bytes(b"\x00" * 64)

    res = _download(client, project, evidence["id"])

    assert res.status_code == 409
    assert "does not match its seal" in res.json()["detail"]


def test_an_erasure_cannot_reach_another_projects_file(client, login, sealed, make_project):
    project, evidence = sealed
    other = make_project(name="Unrelated project")
    login(Role.ADMIN)

    res = _erase(client, {"id": other.id}, evidence["id"])

    assert res.status_code == 404


# --- files sealed before encryption -------------------------------------------------------


@pytest.fixture
def legacy(db, sealed, storage):
    """Turn the sealed file into one stored the pre-#45 way: plaintext, key row with no key.

    That is what the migration leaves behind for every evidence file that already existed.
    """
    project, evidence = sealed
    path = storage / db.get(EvidenceFile, evidence["id"]).storage_key
    path.chmod(0o644)
    path.write_bytes(PDF)
    path.chmod(0o444)
    db.execute(
        update(EvidenceKey)
        .where(EvidenceKey.evidence_id == evidence["id"])
        .values(key=None, nonce=None)
    )
    db.commit()
    return project, evidence


def test_a_file_sealed_before_encryption_still_downloads(client, legacy):
    project, evidence = legacy

    res = _download(client, project, evidence["id"])

    assert res.status_code == 200
    assert res.content == PDF


def test_erasing_a_file_sealed_before_encryption_says_its_plaintext_remains(
    client, db, login, legacy
):
    from app.features.audit.models import LedgerEntry

    project, evidence = legacy
    login(Role.ADMIN)

    assert _erase(client, project, evidence["id"]).status_code == 201

    assert _download(client, project, evidence["id"]).status_code == 410
    entry = db.scalars(select(LedgerEntry).where(LedgerEntry.action == "evidence.erased")).all()[-1]
    assert entry.payload["plaintext_in_storage"] is True


def test_erasing_an_encrypted_file_leaves_no_plaintext(client, db, login, sealed):
    from app.features.audit.models import LedgerEntry

    project, evidence = sealed
    login(Role.ADMIN)

    _erase(client, project, evidence["id"])

    entry = db.scalars(select(LedgerEntry).where(LedgerEntry.action == "evidence.erased")).all()[-1]
    assert entry.payload["plaintext_in_storage"] is False
