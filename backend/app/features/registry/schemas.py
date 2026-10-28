from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PublicationIn(BaseModel):
    """Trusted F3 handoff of public fields, not an HTTP issuance request."""

    model_config = ConfigDict(str_strip_whitespace=True)
    serial: str = Field(min_length=1, max_length=120)
    project_reference: str = Field(min_length=1, max_length=80)
    project_name: str = Field(min_length=1, max_length=200)
    country: str = Field(min_length=1, max_length=100)
    methodology: str = Field(min_length=1, max_length=200)
    vintage: int = Field(ge=1900, le=2200)
    quantity: int = Field(gt=0)
    verifier_name: str = Field(min_length=1, max_length=160)
    verification_reference: str = Field(min_length=1, max_length=80)
    approval_reference: str = Field(min_length=1, max_length=80)
    signed_off_at: datetime
    issued_at: datetime


class CreditOut(PublicationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    verification_status: Literal["approved"] = "approved"
    status: Literal["active", "retired", "revoked"]


class CreditPage(BaseModel):
    items: list[CreditOut]
    total: int
    page: int
    page_size: int


class CreditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    action: Literal["issued", "retired", "revoked"]
    occurred_at: datetime


class CreditDetail(CreditOut):
    history: list[CreditEventOut]
    monitoring: Literal["not_available"] = "not_available"
    ledger_status: Literal["not_available"] = "not_available"


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    summary: str


class EvidencePackOut(BaseModel):
    serial: str
    items: list[EvidenceOut]
    notice: str = "Reviewed buyer-safe summaries only. Original evidence files are not exposed."


class IntegrityOut(BaseModel):
    snapshot_matches: bool
    ledger_status: Literal["not_available"] = "not_available"
    notice: str = (
        "This checks published fields against their stored digest. "
        "Independent authenticity verification requires the F5 audit ledger, not yet connected."
    )
