import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Role(enum.StrEnum):
    """The five roles named in Charter FR-10."""

    DEVELOPER = "developer"
    VERIFIER = "verifier"
    REGISTRY_STAFF = "registry_staff"
    BUYER = "buyer"
    ADMIN = "admin"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    organization: Mapped[str | None] = mapped_column(String(160))
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=32, values_callable=lambda e: [r.value for r in e])
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
