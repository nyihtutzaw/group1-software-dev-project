from functools import lru_cache
from typing import Self

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = "dev-only-change-me-in-production"
MIN_PRODUCTION_JWT_SECRET_BYTES = 32
# Password of the seeded demo accounts in development; it is public (README, sign-in page).
DEVELOPMENT_DEMO_PASSWORD = "crvr-demo"
MIN_PRODUCTION_DEMO_PASSWORD_LENGTH = 12


class OverlapRuleSetting(BaseModel):
    """F2: how much boundary overlap one methodology allows before it blocks issuance."""

    tolerance_pct: float = Field(gt=0, le=100)  # of either project's area
    cap_ha: float = Field(gt=0)  # absolute limit, whatever the project size


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (see docker-compose.yml)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://crvr:crvr@localhost:5432/crvr"
    test_database_url: str = "postgresql+psycopg://crvr:crvr@localhost:5432/crvr_test"

    jwt_secret: str = DEVELOPMENT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    session_cookie: str = "crvr_session"

    seed_demo_users: bool = True
    # The hosted class demo runs as production (Secure cookie, strong JWT secret) but still needs
    # the demo accounts and sample data: DEMO_MODE=true allows them there, with a private
    # DEMO_PASSWORD from Secret Manager instead of the public development one.
    demo_mode: bool = False
    demo_password: str = DEVELOPMENT_DEMO_PASSWORD
    # Behind a proxy (Cloud Run: 1) the client address is this many entries from the right of
    # X-Forwarded-For. 0 = no trusted proxy: use the direct peer and ignore the header.
    forwarded_ip_hops: int = Field(default=0, ge=0)
    # Production image only: the built frontend, served by FastAPI on the same origin as /api.
    static_dir: str = ""
    # Shown when the database is unreachable (e.g. stopped overnight to save cost).
    unavailable_message: str = "CRVR is temporarily unavailable. Please try again in a few minutes."
    storage_dir: str = "/data/evidence"
    # F1: largest evidence file accepted (zipped geo-tagged photo sets are the big ones)
    evidence_max_bytes: int = 50 * 1024 * 1024

    # F2: overlap rules per methodology (change request #43, ADR 0006). An overlap blocks
    # submission and issuance when it is above `tolerance_pct` of either project's area or
    # above `cap_ha` hectares. Override with OVERLAP_RULES as JSON, e.g.
    # OVERLAP_RULES='{"VM0042": {"tolerance_pct": 3.0, "cap_ha": 1.0}}' (replaces the defaults).
    overlap_rules: dict[str, OverlapRuleSetting] = Field(
        default_factory=lambda: {
            "VM0047": OverlapRuleSetting(tolerance_pct=0.5, cap_ha=10.0),  # reforestation
            "VM0042": OverlapRuleSetting(tolerance_pct=3.0, cap_ha=1.0),  # agriculture
            "ACM0003": OverlapRuleSetting(tolerance_pct=1.0, cap_ha=2.0),  # soil carbon
            "VM0033": OverlapRuleSetting(tolerance_pct=1.0, cap_ha=5.0),  # tidal wetland
        }
    )
    # F2: rule for a project with no methodology, or one not listed above (strict).
    overlap_tolerance_pct: float = Field(default=0.5, gt=0, le=100)
    overlap_cap_ha: float = Field(default=2.0, gt=0)
    # F2: largest boundary file accepted for import
    boundary_upload_max_bytes: int = 5 * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def demo_enabled(self) -> bool:
        """Demo accounts and sample data: in development, and in production only with DEMO_MODE."""
        if not self.seed_demo_users:
            return False
        return self.app_env == "development" or (self.is_production and self.demo_mode)

    @property
    def demo_password_is_public(self) -> bool:
        return self.demo_password == DEVELOPMENT_DEMO_PASSWORD

    @model_validator(mode="after")
    def validate_production_demo_password(self) -> Self:
        if (
            self.is_production
            and self.demo_mode
            and (
                self.demo_password_is_public
                or len(self.demo_password) < MIN_PRODUCTION_DEMO_PASSWORD_LENGTH
            )
        ):
            raise ValueError(
                "DEMO_MODE in production requires a private DEMO_PASSWORD with at least "
                f"{MIN_PRODUCTION_DEMO_PASSWORD_LENGTH} characters; load it from Secret Manager."
            )
        return self

    @model_validator(mode="after")
    def validate_production_jwt_secret(self) -> Self:
        if self.is_production:
            secret_length = len(self.jwt_secret.encode("utf-8"))
            if (
                self.jwt_secret == DEVELOPMENT_JWT_SECRET
                or secret_length < MIN_PRODUCTION_JWT_SECRET_BYTES
            ):
                raise ValueError(
                    "Production requires a non-default JWT_SECRET with at least 32 bytes; "
                    "load it from Secret Manager."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
