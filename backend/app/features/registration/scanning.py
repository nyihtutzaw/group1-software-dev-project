"""F1 evidence checks that need the bytes, not the file name (#22).

An upload used to be trusted because its name ended in `.pdf`. Two checks now run after the
upload has been weighed and before it is sealed, because sealing cannot be undone:

1. **What the file actually is** — the declared extension has to match the content. Renaming
   `setup.exe` to `title.pdf` gets it past the extension list but not past here.
2. **Whether it is known malware** — streamed to ClamAV. Evidence is downloaded later by
   registry staff, verifiers and buyers, so the registry should not be the thing that hands
   them a virus.

Both raise `EvidenceRejectedError` with a message meant for the person who uploaded the file.
"""

import socket
import struct
from pathlib import Path
from typing import BinaryIO

# Enough for every signature below; HEIC's brand sits at offset 8.
SNIFF_BYTES = 32
CHUNK = 1024 * 1024
# clamd's own limit is 25 MB by default; ours is the evidence limit.
SCAN_TIMEOUT_SECONDS = 30


class EvidenceRejectedError(Exception):
    """The upload is not what it claims to be, or it is infected. Carries a message to show."""


# --- what the file actually is ----------------------------------------------------------

# A family name per extension. Several extensions share a family: every Office/OpenDocument
# file and a KMZ are ZIP containers, and we do not open them to tell them apart.
FAMILY_BY_EXTENSION = {
    ".pdf": "pdf",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".heic": "heic",
    ".webp": "webp",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".xlsx": "zip",
    ".ods": "zip",
    ".kmz": "zip",
    ".zip": "zip",
    ".xls": "ole2",
    # Text formats have no signature; they are checked by decoding instead.
    ".csv": "text",
    ".gpx": "text",
    ".kml": "text",
    ".geojson": "text",
}

# Longest prefixes first so a more specific signature wins.
SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole2"),
    (b"%PDF-", "pdf"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"II*\x00", "tiff"),
    (b"MM\x00*", "tiff"),
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),  # empty archive
    (b"PK\x07\x08", "zip"),  # spanned archive
]

FAMILY_NAMES = {
    "pdf": "a PDF",
    "jpeg": "a JPEG photo",
    "png": "a PNG image",
    "heic": "a HEIC photo",
    "webp": "a WebP image",
    "tiff": "a TIFF image",
    "zip": "a ZIP-based file (XLSX, ODS, KMZ or ZIP)",
    "ole2": "an older Excel file",
    "text": "a text file (CSV, GPX, KML or GeoJSON)",
}


def detect_family(head: bytes) -> str | None:
    """The file family from its first bytes, or None when nothing is recognised."""
    for signature, family in SIGNATURES:
        if head.startswith(signature):
            return family
    # RIFF....WEBP — the brand is at offset 8, after the container size
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "webp"
    # ISO base media (HEIC/HEIF): a 'ftyp' box whose brand starts with 'hei' or 'mif'
    if head[4:8] == b"ftyp" and head[8:11] in (b"hei", b"mif", b"msf"):
        return "heic"
    if _looks_like_text(head):
        return "text"
    return None


def _looks_like_text(head: bytes) -> bool:
    """Text has no signature, so treat 'decodes as UTF-8 and holds no control bytes' as text."""
    if not head:
        return False
    try:
        decoded = head.lstrip(b"\xef\xbb\xbf").decode("utf-8")
    except UnicodeDecodeError:
        return False
    # Tab, newline and carriage return are the only control characters a CSV or GPX needs.
    return all(character >= " " or character in "\t\n\r" for character in decoded)


def check_content_matches_extension(filename: str, buffer: BinaryIO) -> None:
    """Reject an upload whose bytes do not match the extension it was given.

    The buffer is left rewound. A format we cannot recognise at all is rejected too: an
    accepted extension with unreadable content is exactly what a renamed binary looks like.
    """
    head = buffer.read(SNIFF_BYTES)
    buffer.seek(0)
    extension = Path(filename).suffix.lower()
    expected = FAMILY_BY_EXTENSION.get(extension)
    if expected is None:  # caller checked the extension list first
        return
    found = detect_family(head)
    if found == expected:
        return
    if found is None:
        raise EvidenceRejectedError(
            f"“{filename}” does not look like {FAMILY_NAMES[expected]} inside. "
            "Please upload the original file rather than a renamed one."
        )
    raise EvidenceRejectedError(
        f"“{filename}” is named as {FAMILY_NAMES[expected]} but its content is "
        f"{FAMILY_NAMES[found]}. Please upload it with the right file extension."
    )


# --- known malware ----------------------------------------------------------------------


class VirusScanner:
    """Streams a file to clamd over TCP (the INSTREAM command) and reports the verdict.

    The protocol is small enough to speak directly, which keeps an unmaintained client
    library out of the dependency list.
    """

    def __init__(self, host: str, port: int, *, timeout: float = SCAN_TIMEOUT_SECONDS) -> None:
        self._host, self._port, self._timeout = host, port, timeout

    def scan(self, filename: str, buffer: BinaryIO) -> None:
        """Raise EvidenceRejectedError if clamd reports a signature. The buffer is left rewound."""
        try:
            verdict = self._instream(buffer)
        except OSError as error:
            # Fail closed: an upload that could not be scanned is not sealed. Evidence is
            # permanent, so "we could not check it" must not become "we kept it".
            raise EvidenceRejectedError(
                "The virus scanner is unavailable, so the file was not stored. "
                "Please try again in a few minutes."
            ) from error
        finally:
            buffer.seek(0)
        if verdict is not None:
            raise EvidenceRejectedError(
                f"“{filename}” was rejected by the virus scanner ({verdict}) and was not stored."
            )

    def _instream(self, buffer: BinaryIO) -> str | None:
        """Return the signature name when something is found, or None when the file is clean."""
        with socket.create_connection((self._host, self._port), timeout=self._timeout) as sock:
            sock.settimeout(self._timeout)
            sock.sendall(b"zINSTREAM\0")
            while chunk := buffer.read(CHUNK):
                sock.sendall(struct.pack("!L", len(chunk)) + chunk)
            sock.sendall(struct.pack("!L", 0))  # zero-length chunk ends the stream
            reply = b""
            while b"\0" not in reply:
                received = sock.recv(4096)
                if not received:
                    break
                reply += received
        answer = reply.rstrip(b"\0").decode("utf-8", "replace").strip()
        # "stream: OK" · "stream: Eicar-Test-Signature FOUND" · "... ERROR"
        if answer.endswith("FOUND"):
            return answer.removeprefix("stream:").removesuffix("FOUND").strip()
        if answer.endswith("OK"):
            return None
        raise OSError(f"clamd answered {answer!r}")


class NoVirusScanner:
    """Used where no clamd is reachable (plain `pytest`, a laptop without the container)."""

    def scan(self, filename: str, buffer: BinaryIO) -> None:
        return None
