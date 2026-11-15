from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.auth.models import Role

# Emails are plain strings here: sign-in only compares them with stored accounts.
# Validate format (EmailStr) where accounts are created, so demo/test domains like
# *.local keep working.


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    organization: str | None
    role: Role


class AdminUserOut(UserOut):
    is_active: bool


class AdminUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=255)
    full_name: str = Field(min_length=1, max_length=120)
    organization: str | None = Field(default=None, max_length=160)
    role: Role
    initial_password: str = Field(min_length=12, max_length=72)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("organization", mode="before")
    @classmethod
    def normalize_organization(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("initial_password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "AdminUserUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if ("role" in self.model_fields_set and self.role is None) or (
            "is_active" in self.model_fields_set and self.is_active is None
        ):
            raise ValueError("Updated fields cannot be null")
        return self


class DemoAccount(BaseModel):
    email: str
    full_name: str
    role: Role
