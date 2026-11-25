"""Request and response models for the verification workflow."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.features.verification.models import (
    CHECKLIST,
    ApprovalDecision,
    AssignmentStatus,
    ReportDecision,
    RiskRating,
)

ChipTone = Literal["ok", "wait", "warn", "draft", "accent"]


class AssignIn(BaseModel):
    project_id: int
    verifier_id: int
    due_date: date


class ReportIn(BaseModel):
    checklist: dict[str, bool]
    note: str = Field(min_length=1, max_length=4000)
    decision: ReportDecision
    risk_rating: RiskRating | None = None

    @model_validator(mode="after")
    def complete_checklist(self) -> "ReportIn":
        expected = {key for key, _label in CHECKLIST}
        if set(self.checklist) != expected:
            raise ValueError("Checklist must contain exactly the five review items")
        if self.decision == ReportDecision.SIGN_OFF and self.risk_rating is None:
            raise ValueError("A sign-off must include a reversal risk rating")
        return self


class ReassignIn(BaseModel):
    verifier_id: int
    due_date: date


class ApprovalIn(BaseModel):
    decision: ApprovalDecision
    rationale: str = Field(min_length=5, max_length=4000)


class QueueItem(BaseModel):
    id: int
    project_id: int
    project_code: str
    project_name: str
    verifier_name: str
    due_date: date
    overdue: bool
    days_overdue: int
    status: AssignmentStatus
    chip: str
    chip_tone: ChipTone


class QueueOut(BaseModel):
    items: list[QueueItem]
    assigned_count: int
    overdue_count: int
    signed_off_this_year: int


class EvidenceLine(BaseModel):
    title: str
    detail: str
    # Set for a sealed file: the page links it to F1's download (and View for PDFs and photos).
    evidence_id: int | None = None
    viewable: bool = False
    # Content destroyed to remove personal data (#45): nothing left to open.
    erased: bool = False


class AutoCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class CheckLine(BaseModel):
    key: str
    label: str
    source: str
    checked: bool


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    decision: ApprovalDecision
    rationale: str
    approver_name: str
    decided_at: datetime


class ChainEvent(BaseModel):
    id: str
    kind: Literal["assigned", "report", "approval", "reassigned"]
    at: datetime
    actor_name: str
    summary: str
    note: str | None = None


class IssuanceOut(BaseModel):
    """The credits issued for this review's approval: the sellable batch and its buffer."""

    credit_id: int
    vintage: int
    quantity: int
    buffer_quantity: int


class ReviewOut(BaseModel):
    item: QueueItem
    evidence: list[EvidenceLine]
    automatic_checks: list[AutoCheck]
    checklist: list[CheckLine]
    note: str
    risk_rating: RiskRating | None
    can_submit: bool
    can_reassign: bool
    can_decide: bool
    decision_block: str | None
    report_id: int | None
    approval: ApprovalOut | None
    chain: list[ChainEvent]
    # Issuing credits after approval (staff): the buffer share comes from the reversal risk
    buffer_percent: int | None = None
    can_issue: bool = False
    issuance: IssuanceOut | None = None


class ChainOut(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    chain: list[ChainEvent]


class NoteOut(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    # changes_requested: the verifier's note · rejected: the registry staff rationale
    kind: Literal["changes_requested", "rejected"]
    note: str
    at: datetime


class VerifierOut(BaseModel):
    id: int
    full_name: str
    email: str


class IssueIn(BaseModel):
    """Explicit staff-confirmed batch values; approval alone does not issue estimates."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    country: str = Field(min_length=2, max_length=100)
    vintage: int = Field(ge=1900, le=2200, strict=True)
    quantity: int = Field(gt=0, le=1_000_000_000, strict=True)
