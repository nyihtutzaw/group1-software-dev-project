"""Request and response models for the verification workflow."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.features.verification.models import (
    CHECKLIST,
    ApprovalDecision,
    AssignmentStatus,
    ReportDecision,
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

    @model_validator(mode="after")
    def complete_checklist(self) -> "ReportIn":
        expected = {key for key, _label in CHECKLIST}
        if set(self.checklist) != expected:
            raise ValueError("Checklist must contain exactly the five review items")
        return self


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
    kind: Literal["assigned", "report", "approval"]
    at: datetime
    actor_name: str
    summary: str
    note: str | None = None


class ReviewOut(BaseModel):
    item: QueueItem
    evidence: list[EvidenceLine]
    automatic_checks: list[AutoCheck]
    checklist: list[CheckLine]
    note: str
    can_submit: bool
    can_decide: bool
    decision_block: str | None
    report_id: int | None
    approval: ApprovalOut | None
    chain: list[ChainEvent]


class ChainOut(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    chain: list[ChainEvent]


class NoteOut(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    note: str
    at: datetime


class VerifierOut(BaseModel):
    id: int
    full_name: str
    email: str
