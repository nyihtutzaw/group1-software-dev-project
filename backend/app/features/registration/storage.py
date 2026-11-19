"""F1 evidence storage — write-once backends (FR-02, WBS 4.2.2).

Development keeps evidence in a local Docker volume; production writes it to the private
Cloud Storage bucket created by `infra/gcp/bootstrap.sh`, whose locked retention policy is
what actually enforces the agreed seven-year period.

Neither backend has an update or a delete method. Write-once is a property of the interface,
not a rule each caller has to remember. A file that is rejected for being empty or too large
never reaches the backend at all: `seal()` is handed a stream only after the size is known.
"""

import hashlib
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

# Files up to this size are weighed in memory; larger ones spool to a temporary file.
SPOOL_MAX_BYTES = 8 * 1024 * 1024
CHUNK = 1024 * 1024


class EvidenceEmptyError(Exception):
    """The upload held no bytes. Nothing was sealed."""


class EvidenceTooLargeError(Exception):
    """The upload was longer than the configured limit. Nothing was sealed."""


class EvidenceMissingError(Exception):
    """The row exists but its stored object does not."""


def weigh(stream: BinaryIO, *, max_bytes: int) -> tuple[SpooledTemporaryFile[bytes], str, int]:
    """Read an upload once: hash it, measure it, and hold it until it is known to be acceptable.

    Returns an open, rewound buffer plus the SHA-256 digest and the size. The caller closes the
    buffer. Raises before any backend is touched, so a rejected upload leaves no partial object —
    which matters on a bucket with a retention lock, where a partial object could not be deleted.
    """
    digest, size = hashlib.sha256(), 0
    # Deliberately not a context manager: the caller owns and closes the buffer.
    buffer: SpooledTemporaryFile[bytes] = SpooledTemporaryFile(max_size=SPOOL_MAX_BYTES)  # noqa: SIM115
    try:
        while chunk := stream.read(CHUNK):
            size += len(chunk)
            if size > max_bytes:
                raise EvidenceTooLargeError
            digest.update(chunk)
            buffer.write(chunk)
        if size == 0:
            raise EvidenceEmptyError
    except Exception:
        buffer.close()
        raise
    buffer.seek(0)
    return buffer, digest.hexdigest(), size


class EvidenceStorage(ABC):
    """Seal a file under a key, and read it back. Deliberately no update and no delete."""

    @abstractmethod
    def seal(self, key: str, buffer: BinaryIO) -> None:
        """Write the buffer at `key`, failing if anything is already there."""

    @abstractmethod
    def open(self, key: str) -> BinaryIO:
        """Open the sealed object for reading. Raises EvidenceMissingError if it is gone."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Whether a sealed object is stored under this key."""


class LocalEvidenceStorage(EvidenceStorage):
    """A directory on a Docker volume. Used in development and in the test suite."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def _path(self, key: str) -> Path:
        return self._root / key

    def seal(self, key: str, buffer: BinaryIO) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # "xb": fail rather than overwrite if the key somehow exists already
        with path.open("xb") as out:
            shutil.copyfileobj(buffer, out, CHUNK)
        path.chmod(0o444)

    def open(self, key: str) -> BinaryIO:
        path = self._path(key)
        if not path.is_file():
            raise EvidenceMissingError(key)
        return path.open("rb")

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class GcsEvidenceStorage(EvidenceStorage):
    """A private Cloud Storage bucket. The bucket's retention lock is what makes it write-once.

    `google-cloud-storage` is imported only when a real client is needed, so development and the
    tests never load it; the tests pass their own client in.
    """

    def __init__(self, bucket: str, *, client: object | None = None) -> None:
        self._bucket_name = bucket
        self._client = client

    def _blob(self, key: str) -> object:
        if self._client is None:
            from google.cloud import storage  # noqa: PLC0415 — production-only import

            self._client = storage.Client()
        return self._client.bucket(self._bucket_name).blob(key)  # type: ignore[attr-defined]

    def seal(self, key: str, buffer: BinaryIO) -> None:
        # if_generation_match=0 is the bucket's version of open("xb"): the write fails if an
        # object already exists at this key, so a retry can never overwrite sealed evidence.
        self._blob(key).upload_from_file(buffer, if_generation_match=0)  # type: ignore[attr-defined]

    def open(self, key: str) -> BinaryIO:
        blob = self._blob(key)
        if not blob.exists():  # type: ignore[attr-defined]
            raise EvidenceMissingError(key)
        return blob.open("rb")  # type: ignore[attr-defined,no-any-return]

    def exists(self, key: str) -> bool:
        return bool(self._blob(key).exists())  # type: ignore[attr-defined]


def build_storage(backend: str, *, storage_dir: str, bucket: str) -> EvidenceStorage:
    """Pick the backend named in the settings. Unknown names are a configuration error."""
    if backend == "gcs":
        return GcsEvidenceStorage(bucket)
    if backend == "local":
        return LocalEvidenceStorage(storage_dir)
    raise ValueError(f"Unknown evidence backend {backend!r}: expected 'local' or 'gcs'")
