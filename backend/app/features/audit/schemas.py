from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    action: str
    actor_id: int | None
    actor_email: str | None
    actor_role: str | None
    entity: str
    entity_id: int
    payload: dict[str, Any]
    prev_hash: str
    hash: str


class LedgerVerificationOut(BaseModel):
    valid: bool
    error: str | None = None


class LedgerPageOut(BaseModel):
    items: list[LedgerEntryOut]
    total: int
    page: int
    page_size: int
