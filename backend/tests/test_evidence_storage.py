"""F1 evidence storage backends — one test (or more) per acceptance criterion of issue #20.

The bucket backend is exercised against a fake Cloud Storage client: the tests never reach the
network and never need `google-cloud-storage` installed.
"""

import hashlib
import io
import stat

import pytest
from pydantic import ValidationError

from app.auth.models import Role
from app.core.config import Settings, get_settings
from app.features.registration import service
from app.features.registration.storage import (
    EvidenceEmptyError,
    EvidenceMissingError,
    EvidenceTooLargeError,
    GcsEvidenceStorage,
    LocalEvidenceStorage,
    build_storage,
    weigh,
)

PDF = b"%PDF-1.7 land title"
KEY = "7/abc123.pdf"


# --- the fake bucket -------------------------------------------------------------------


class FakeBlob:
    def __init__(self, store: dict[str, bytes], key: str) -> None:
        self._store, self._key = store, key

    def upload_from_file(
        self, buffer: io.BufferedIOBase, *, if_generation_match: int | None = None
    ):
        # The real client refuses the write when the object already exists; so do we.
        if if_generation_match == 0 and self._key in self._store:
            raise RuntimeError(f"412 Precondition Failed: {self._key} already exists")
        self._store[self._key] = buffer.read()

    def exists(self) -> bool:
        return self._key in self._store

    def open(self, mode: str) -> io.BytesIO:
        return io.BytesIO(self._store[self._key])


class FakeBucket:
    def __init__(self, store: dict[str, bytes]) -> None:
        self._store = store

    def blob(self, key: str) -> FakeBlob:
        return FakeBlob(self._store, key)


class FakeClient:
    """Stands in for google.cloud.storage.Client — only the three calls we make."""

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}
        self.buckets: list[str] = []

    def bucket(self, name: str) -> FakeBucket:
        self.buckets.append(name)
        return FakeBucket(self.store)


@pytest.fixture
def gcs() -> tuple[GcsEvidenceStorage, FakeClient]:
    client = FakeClient()
    return GcsEvidenceStorage("crvr-evidence", client=client), client


# --- choosing the backend (config switch) ----------------------------------------------


def test_development_defaults_to_the_local_volume():
    assert Settings().evidence_backend == "local"


@pytest.mark.parametrize(
    ("backend", "expected"),
    [("local", LocalEvidenceStorage), ("gcs", GcsEvidenceStorage)],
)
def test_the_setting_picks_the_backend(backend, expected):
    storage = build_storage(backend, storage_dir="/data/evidence", bucket="crvr-evidence")
    assert isinstance(storage, expected)


def test_an_unknown_backend_name_is_a_configuration_error():
    with pytest.raises(ValueError, match="Unknown evidence backend"):
        build_storage("s3", storage_dir="/data/evidence", bucket="")


def test_the_bucket_backend_without_a_bucket_is_refused():
    with pytest.raises(ValidationError, match="EVIDENCE_BUCKET"):
        Settings(evidence_backend="gcs", evidence_bucket="  ")


def test_the_bucket_backend_with_a_bucket_is_accepted():
    assert Settings(evidence_backend="gcs", evidence_bucket="crvr-evidence").evidence_bucket


# --- weighing the upload before anything is sealed --------------------------------------


def test_the_upload_is_hashed_and_measured_once():
    buffer, sha256, size = weigh(io.BytesIO(PDF), max_bytes=1024)

    assert buffer.read() == PDF
    assert sha256 == hashlib.sha256(PDF).hexdigest()
    assert size == len(PDF)
    buffer.close()


@pytest.mark.parametrize(
    ("data", "limit", "problem"),
    [(b"", 1024, EvidenceEmptyError), (b"x" * 20, 10, EvidenceTooLargeError)],
)
def test_a_rejected_upload_never_reaches_a_backend(data, limit, problem, tmp_path):
    storage = LocalEvidenceStorage(tmp_path)

    with pytest.raises(problem):
        weigh(io.BytesIO(data), max_bytes=limit)

    assert not list(tmp_path.rglob("*"))
    assert not storage.exists(KEY)


# --- both backends behave the same way --------------------------------------------------


def test_local_seals_the_file_read_only(tmp_path):
    storage = LocalEvidenceStorage(tmp_path)

    storage.seal(KEY, io.BytesIO(PDF))

    path = tmp_path / KEY
    assert path.read_bytes() == PDF
    assert not path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)


def test_bucket_seals_the_file_and_refuses_to_overwrite_it(gcs):
    storage, client = gcs

    storage.seal(KEY, io.BytesIO(PDF))

    assert client.store[KEY] == PDF
    assert client.buckets == ["crvr-evidence"]
    with pytest.raises(RuntimeError, match="already exists"):
        storage.seal(KEY, io.BytesIO(b"forged"))
    assert client.store[KEY] == PDF


def test_local_refuses_to_overwrite_a_sealed_file(tmp_path):
    storage = LocalEvidenceStorage(tmp_path)
    storage.seal(KEY, io.BytesIO(PDF))

    with pytest.raises(FileExistsError):
        storage.seal(KEY, io.BytesIO(b"forged"))

    assert (tmp_path / KEY).read_bytes() == PDF


def test_neither_backend_offers_an_update_or_a_delete(tmp_path, gcs):
    for storage in (LocalEvidenceStorage(tmp_path), gcs[0]):
        for forbidden in ("update", "delete", "remove", "replace", "unlink", "write"):
            assert not hasattr(storage, forbidden), f"{type(storage).__name__}.{forbidden}"


def test_local_reads_back_the_exact_bytes(tmp_path):
    storage = LocalEvidenceStorage(tmp_path)
    storage.seal(KEY, io.BytesIO(PDF))

    with storage.open(KEY) as stream:
        assert stream.read() == PDF
    assert storage.exists(KEY)


def test_bucket_reads_back_the_exact_bytes(gcs):
    storage, _ = gcs
    storage.seal(KEY, io.BytesIO(PDF))

    with storage.open(KEY) as stream:
        assert stream.read() == PDF
    assert storage.exists(KEY)


@pytest.mark.parametrize("backend", ["local", "gcs"])
def test_a_missing_object_is_reported_not_guessed(backend, tmp_path, gcs):
    storage = LocalEvidenceStorage(tmp_path) if backend == "local" else gcs[0]

    assert not storage.exists(KEY)
    with pytest.raises(EvidenceMissingError):
        storage.open(KEY)


# --- the whole upload route, running on the bucket backend ------------------------------


def test_upload_and_download_work_on_the_bucket_backend(client, login, monkeypatch, gcs):
    """Issue #20: production behaviour, end to end, without touching the local volume."""
    storage, fake = gcs
    monkeypatch.setattr(service, "get_storage", lambda: storage)
    monkeypatch.setattr(get_settings(), "evidence_backend", "gcs")
    login(Role.DEVELOPER)
    project = client.post("/api/projects", json={"name": "Bucket-backed project"}).json()

    sealed = client.post(
        f"/api/projects/{project['id']}/evidence",
        files={"file": ("title.pdf", PDF, "application/pdf")},
        data={"kind": "land_title"},
    )

    assert sealed.status_code == 201, sealed.text
    body = sealed.json()
    assert body["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert body["size_bytes"] == len(PDF)
    # The bytes went to the bucket, and only to the bucket
    assert list(fake.store.values()) == [PDF]

    downloaded = client.get(f"/api/projects/{project['id']}/evidence/{body['id']}/file")

    assert downloaded.status_code == 200
    assert downloaded.content == PDF


def test_a_rejected_upload_leaves_the_bucket_empty(client, login, monkeypatch, gcs):
    storage, fake = gcs
    monkeypatch.setattr(service, "get_storage", lambda: storage)
    monkeypatch.setattr(get_settings(), "evidence_max_bytes", 10)
    login(Role.DEVELOPER)
    project = client.post("/api/projects", json={"name": "Bucket-backed project"}).json()
    url = f"/api/projects/{project['id']}/evidence"

    empty = client.post(
        url, files={"file": ("a.pdf", b"", "application/pdf")}, data={"kind": "other"}
    )
    big = client.post(
        url, files={"file": ("b.pdf", b"x" * 11, "application/pdf")}, data={"kind": "other"}
    )

    assert empty.status_code == 422
    assert big.status_code == 413
    assert fake.store == {}
