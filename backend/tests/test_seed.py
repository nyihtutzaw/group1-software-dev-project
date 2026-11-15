import pytest

from app.core.config import get_settings
from app.seed import seed_demo_data, seed_demo_users


def test_seed_demo_users_refuses_production(monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")

    with pytest.raises(RuntimeError, match="APP_ENV=production"):
        seed_demo_users()


def test_seed_demo_data_refuses_production(monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")

    with pytest.raises(RuntimeError, match="APP_ENV=production"):
        seed_demo_data()
