"""Hosted demo settings: DEMO_MODE, proxy client IPs, the bundled frontend, database outages."""

from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.core.config import DEVELOPMENT_DEMO_PASSWORD, Settings, get_settings
from app.core.db import get_db
from app.core.frontend import mount_frontend
from app.demo_reset import reset_demo_database
from app.features.audit.security_log import client_ip
from app.main import app
from app.seed import _ensure_demo_seeding_allowed

PRODUCTION = {"app_env": "production", "jwt_secret": "A" * 32}


# --- DEMO_MODE -------------------------------------------------------------------------------


def test_production_demo_mode_rejects_the_public_demo_password():
    with pytest.raises(ValidationError, match="DEMO_PASSWORD"):
        Settings(**PRODUCTION, demo_mode=True, demo_password=DEVELOPMENT_DEMO_PASSWORD)


def test_production_demo_mode_rejects_a_short_demo_password():
    with pytest.raises(ValidationError, match="DEMO_PASSWORD"):
        Settings(**PRODUCTION, demo_mode=True, demo_password="short")


def test_demo_password_error_does_not_expose_the_password():
    with pytest.raises(ValidationError) as error:
        Settings(**PRODUCTION, demo_mode=True, demo_password="secret-ish")
    assert "secret-ish" not in str(error.value)


def test_demo_password_ignores_surrounding_whitespace():
    settings = Settings(**PRODUCTION, demo_mode=True, demo_password="a-private-demo-pw\n")

    assert settings.demo_password == "a-private-demo-pw"


@pytest.mark.parametrize(
    ("overrides", "enabled"),
    [
        ({"app_env": "development"}, True),
        ({"app_env": "development", "seed_demo_users": False}, False),
        (PRODUCTION, False),
        ({**PRODUCTION, "demo_mode": True, "demo_password": "a-private-demo-pw"}, True),
        (
            {**PRODUCTION, "demo_mode": True, "demo_password": "a-private-demo-pw"}
            | {"seed_demo_users": False},
            False,
        ),
    ],
)
def test_demo_enabled(overrides, enabled):
    assert Settings(**overrides).demo_enabled is enabled


def test_seeding_is_allowed_in_production_only_with_demo_mode(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(RuntimeError, match="DEMO_MODE"):
        _ensure_demo_seeding_allowed()

    monkeypatch.setattr(settings, "demo_mode", True)
    _ensure_demo_seeding_allowed()


def test_demo_reset_refuses_outside_demo_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")

    with pytest.raises(RuntimeError, match="only for demo data"):
        reset_demo_database()


def test_demo_accounts_include_the_public_password_in_development(client):
    accounts = client.get("/api/auth/demo-accounts").json()

    assert accounts
    assert {account["password"] for account in accounts} == {DEVELOPMENT_DEMO_PASSWORD}


def test_demo_accounts_are_not_listed_on_the_hosted_demo(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "demo_password", "a-private-demo-pw")

    assert client.get("/api/auth/demo-accounts").json() == []


def test_demo_accounts_are_empty_in_production_without_demo_mode(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")

    assert client.get("/api/auth/demo-accounts").json() == []


# --- client IP behind a proxy ----------------------------------------------------------------


def _request(forwarded: str | None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": ("10.0.0.9", 443)})


def test_client_ip_ignores_forwarded_header_without_a_trusted_proxy(monkeypatch):
    monkeypatch.setattr(get_settings(), "forwarded_ip_hops", 0)

    assert client_ip(_request("203.0.113.7")) == "10.0.0.9"


def test_client_ip_takes_the_entry_added_by_the_trusted_proxy(monkeypatch):
    monkeypatch.setattr(get_settings(), "forwarded_ip_hops", 1)

    # The client forged "1.1.1.1"; Cloud Run appended the real address on the right.
    assert client_ip(_request("1.1.1.1, 203.0.113.7")) == "203.0.113.7"


def test_client_ip_falls_back_to_the_peer_when_the_header_is_missing(monkeypatch):
    monkeypatch.setattr(get_settings(), "forwarded_ip_hops", 1)

    assert client_ip(_request(None)) == "10.0.0.9"


# --- database outage -------------------------------------------------------------------------


def test_database_outage_returns_503_with_a_readable_message(monkeypatch):
    monkeypatch.setattr(get_settings(), "unavailable_message", "CRVR is closed for the night.")

    def unavailable(request: Request):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_db] = unavailable
    try:
        res = TestClient(app).get("/api/health")
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 503
    assert res.json() == {"detail": "CRVR is closed for the night."}


# --- bundled frontend ------------------------------------------------------------------------


@pytest.fixture
def frontend(tmp_path: Path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets" / "app-1a2b.js").write_text("console.log(1)")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path.parent / "secret.txt").write_text("outside")

    web = FastAPI()

    @web.get("/api/ping")
    def ping() -> dict[str, str]:
        return {"pong": "yes"}

    mount_frontend(web, str(tmp_path))
    return TestClient(web)


def test_frontend_serves_the_app_for_client_side_routes(frontend):
    for path in ("/", "/projects/12", "/ledger"):
        res = frontend.get(path)
        assert res.status_code == 200
        assert "<div id=root>" in res.text
        assert res.headers["cache-control"] == "no-cache"


def test_frontend_serves_fingerprinted_assets_with_long_caching(frontend):
    res = frontend.get("/assets/app-1a2b.js")

    assert res.status_code == 200
    assert "immutable" in res.headers["cache-control"]


def test_frontend_serves_public_files(frontend):
    assert frontend.get("/favicon.svg").text == "<svg/>"


def test_frontend_leaves_api_routes_and_unknown_api_paths_alone(frontend):
    assert frontend.get("/api/ping").json() == {"pong": "yes"}
    res = frontend.get("/api/nope")
    assert res.status_code == 404
    assert res.json() == {"detail": "Not Found"}


def test_frontend_does_not_serve_files_outside_its_directory(frontend):
    res = frontend.get("/..%2Fsecret.txt")

    assert "outside" not in res.text


def test_frontend_requires_a_built_index(tmp_path):
    with pytest.raises(RuntimeError, match="index.html"):
        mount_frontend(FastAPI(), str(tmp_path))
