"""F1 upload checks — one test (or more) per acceptance criterion of issue #22.

The virus-scanner tests talk the real clamd INSTREAM protocol to a fake clamd running in a
thread, so the EICAR case is exercised without the 1 GB container. A second test runs against
a real clamd when one is reachable and skips when it is not.
"""

import socket
import struct
import threading
from collections.abc import Iterator

import pytest

from app.auth.models import Role
from app.core.config import get_settings
from app.features.registration import service
from app.features.registration.scanning import (
    EvidenceRejectedError,
    NoVirusScanner,
    VirusScanner,
    check_content_matches_extension,
    detect_family,
)

# The standard anti-malware test string. Split so this file is not itself flagged.
EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
PDF = b"%PDF-1.7 land title"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
ZIP = b"PK\x03\x04" + b"\x00" * 24
EXE = b"MZ\x90\x00\x03" + b"\x00" * 24
GPX = b'<?xml version="1.0"?><gpx version="1.1"><wpt lat="18.7" lon="100.7"/></gpx>'


# --- a fake clamd ------------------------------------------------------------------------


class FakeClamd(threading.Thread):
    """Speaks just enough INSTREAM to answer OK or FOUND."""

    def __init__(self, *, answer: bytes | None = None) -> None:
        super().__init__(daemon=True)
        self._answer = answer
        self._server = socket.socket()
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(1)
        self.port: int = self._server.getsockname()[1]
        self.received = bytearray()

    def run(self) -> None:
        try:
            connection, _ = self._server.accept()
        except OSError:
            return
        with connection:
            # TCP does not preserve send boundaries: the command and the first chunks can
            # arrive together, so buffer and take exactly what the protocol asks for.
            buffer = bytearray()

            def take(count: int) -> bytes | None:
                while len(buffer) < count:
                    received = connection.recv(65536)
                    if not received:
                        return None
                    buffer.extend(received)
                taken = bytes(buffer[:count])
                del buffer[:count]
                return taken

            while b"\0" not in buffer:  # zINSTREAM\0
                received = connection.recv(65536)
                if not received:
                    return
                buffer.extend(received)
            del buffer[: buffer.index(b"\0") + 1]

            while True:
                header = take(4)
                if header is None:
                    return
                (length,) = struct.unpack("!L", header)
                if length == 0:
                    break
                body = take(length)
                if body is None:
                    return
                self.received += body
            if self._answer is not None:
                reply = self._answer
            elif EICAR in self.received:
                reply = b"stream: Eicar-Test-Signature FOUND\0"
            else:
                reply = b"stream: OK\0"
            connection.sendall(reply)

    def close(self) -> None:
        self._server.close()


@pytest.fixture
def clamd() -> Iterator[FakeClamd]:
    server = FakeClamd()
    server.start()
    yield server
    server.close()


# --- 1. the file type comes from the content ---------------------------------------------


@pytest.mark.parametrize(
    ("head", "family"),
    [
        (PDF, "pdf"),
        (PNG, "png"),
        (b"\xff\xd8\xff\xe0", "jpeg"),
        (ZIP, "zip"),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole2"),
        (b"II*\x00", "tiff"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "webp"),
        (b"\x00\x00\x00\x18ftypheic", "heic"),
        (GPX, "text"),
        (b"name,area\nNan,12\n", "text"),
        (EXE, None),
        (b"\x00\x01\x02\x03", None),
    ],
)
def test_the_family_is_read_from_the_first_bytes(head, family):
    assert detect_family(head) == family


@pytest.mark.parametrize(
    ("filename", "data"),
    [
        ("title.pdf", PDF),
        ("site.png", PNG),
        ("readings.xlsx", ZIP),
        ("boundary.kmz", ZIP),
        ("track.gpx", GPX),
        ("plots.csv", b"id,area\n1,12\n"),
    ],
)
def test_a_genuine_file_passes(filename, data, tmp_path):
    check_content_matches_extension(filename, _buffer(data))


def test_a_renamed_executable_is_refused(tmp_path):
    """The acceptance criterion: `setup.exe` renamed to `title.pdf` must not get through."""
    with pytest.raises(EvidenceRejectedError, match="does not look like a PDF"):
        check_content_matches_extension("title.pdf", _buffer(EXE))


def test_a_file_with_the_wrong_extension_names_both_formats():
    with pytest.raises(EvidenceRejectedError, match="named as a PDF .* content is a PNG"):
        check_content_matches_extension("title.pdf", _buffer(PNG))


def test_the_buffer_is_left_rewound_for_the_next_step():
    buffer = _buffer(PDF)
    check_content_matches_extension("title.pdf", buffer)
    assert buffer.read() == PDF


# --- 2. known malware is refused ----------------------------------------------------------


def test_a_clean_file_is_passed_through(clamd):
    scanner = VirusScanner("127.0.0.1", clamd.port)

    scanner.scan("title.pdf", _buffer(PDF))

    assert bytes(clamd.received) == PDF


def test_the_eicar_test_file_is_refused(clamd):
    """The acceptance criterion: a test-virus file is rejected before it can be sealed."""
    scanner = VirusScanner("127.0.0.1", clamd.port)

    with pytest.raises(EvidenceRejectedError, match="Eicar-Test-Signature"):
        scanner.scan("notes.pdf", _buffer(b"%PDF-1.7 " + EICAR))


def test_an_unreachable_scanner_refuses_the_upload_rather_than_sealing_it():
    """Fail closed: evidence is permanent, so 'not checked' must not become 'kept'."""
    with socket.socket() as probe:  # a port nothing is listening on
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    scanner = VirusScanner("127.0.0.1", port, timeout=1)

    with pytest.raises(EvidenceRejectedError, match="scanner is unavailable"):
        scanner.scan("title.pdf", _buffer(PDF))


def test_scanning_is_skipped_when_it_is_switched_off():
    assert NoVirusScanner().scan("title.pdf", _buffer(b"%PDF-1.7 " + EICAR)) is None


def test_the_settings_choose_the_scanner(monkeypatch):
    monkeypatch.setattr(get_settings(), "virus_scan_enabled", False)
    assert isinstance(service.get_scanner(), NoVirusScanner)
    monkeypatch.setattr(get_settings(), "virus_scan_enabled", True)
    assert isinstance(service.get_scanner(), VirusScanner)


# --- 3. the upload route refuses both, with a message -------------------------------------


def test_a_renamed_binary_is_refused_by_the_api_and_nothing_is_stored(client, draft, storage):
    _, project = draft

    res = _upload(client, project["id"], "title.pdf", EXE)

    assert res.status_code == 415
    assert "does not look like a PDF" in res.json()["detail"]
    assert not [p for p in storage.rglob("*") if p.is_file()]
    assert client.get(f"/api/projects/{project['id']}").json()["evidence"] == []


def test_an_infected_file_is_refused_by_the_api_and_nothing_is_stored(
    client, draft, storage, monkeypatch, clamd
):
    _, project = draft
    monkeypatch.setattr(get_settings(), "virus_scan_enabled", True)
    monkeypatch.setattr(get_settings(), "clamav_host", "127.0.0.1")
    monkeypatch.setattr(get_settings(), "clamav_port", clamd.port)

    res = _upload(client, project["id"], "notes.pdf", b"%PDF-1.7 " + EICAR)

    assert res.status_code == 415
    assert "virus scanner" in res.json()["detail"]
    assert not [p for p in storage.rglob("*") if p.is_file()]


def test_a_clean_file_is_still_sealed_with_scanning_on(client, draft, monkeypatch, clamd):
    _, project = draft
    monkeypatch.setattr(get_settings(), "virus_scan_enabled", True)
    monkeypatch.setattr(get_settings(), "clamav_host", "127.0.0.1")
    monkeypatch.setattr(get_settings(), "clamav_port", clamd.port)

    res = _upload(client, project["id"], "title.pdf", PDF)

    assert res.status_code == 201, res.text


# --- 4. against a real clamd, when there is one -------------------------------------------


def _clamd_available(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.mark.skipif(
    not _clamd_available(get_settings().clamav_host, get_settings().clamav_port),
    reason="clamd is not running (docker compose --profile scan up -d clamav)",
)
def test_real_clamd_finds_the_eicar_file():
    settings = get_settings()
    scanner = VirusScanner(settings.clamav_host, settings.clamav_port)

    scanner.scan("title.pdf", _buffer(PDF))  # clean file passes
    with pytest.raises(EvidenceRejectedError, match="rejected by the virus scanner"):
        scanner.scan("notes.pdf", _buffer(EICAR))


# --- helpers -------------------------------------------------------------------------------


def _buffer(data: bytes):
    import io

    return io.BytesIO(data)


def _upload(client, project_id: int, filename: str, data: bytes):
    return client.post(
        f"/api/projects/{project_id}/evidence",
        files={"file": (filename, data, "application/octet-stream")},
        data={"kind": "other"},
    )


@pytest.fixture
def draft(client, login):
    login(Role.DEVELOPER)
    return None, client.post("/api/projects", json={"name": "Scan test project"}).json()


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_dir", str(tmp_path))
    return tmp_path
