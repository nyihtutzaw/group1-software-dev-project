from pydantic import BaseModel, ConfigDict

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


class DemoAccount(BaseModel):
    email: str
    full_name: str
    role: Role
