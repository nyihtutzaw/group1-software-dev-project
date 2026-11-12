from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OverlapRuleSetting(BaseModel):
    """F2: how much boundary overlap one methodology allows before it blocks issuance."""

    tolerance_pct: float = Field(gt=0, le=100)  # of either project's area
    cap_ha: float = Field(gt=0)  # absolute limit, whatever the project size


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (see docker-compose.yml)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://crvr:crvr@localhost:5432/crvr"
    test_database_url: str = "postgresql+psycopg://crvr:crvr@localhost:5432/crvr_test"

    jwt_secret: str = "dev-only-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    session_cookie: str = "crvr_session"

    seed_demo_users: bool = True
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
