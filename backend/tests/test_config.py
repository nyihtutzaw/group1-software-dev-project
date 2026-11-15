import pytest
from pydantic import ValidationError

from app.core.config import DEVELOPMENT_JWT_SECRET, Settings


def test_production_settings_reject_development_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret=DEVELOPMENT_JWT_SECRET)


def test_production_settings_reject_short_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret="short")


def test_production_validation_error_does_not_expose_jwt_secret():
    secret = "short-secret-value"

    with pytest.raises(ValidationError) as error:
        Settings(app_env="production", jwt_secret=secret)

    assert secret not in str(error.value)


def test_production_settings_accept_long_random_jwt_secret():
    settings = Settings(app_env="production", jwt_secret="A" * 32)

    assert settings.is_production


def test_development_settings_keep_the_development_jwt_default():
    settings = Settings(app_env="development")

    assert settings.jwt_secret == DEVELOPMENT_JWT_SECRET
