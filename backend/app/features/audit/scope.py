"""Which ledger entries each role may read, and how much of an entry a buyer sees.

Registry staff and admins read the whole ledger. A verifier reads the entries of the projects
currently assigned to them (WBS 7.1.1). A buyer reads the entries of the projects they were
granted (WBS 8.1.1), without who did what and with only the traceability fields of the payload,
so developer-sensitive data never reaches a buyer account (WBS 8.3.1).
"""

from sqlalchemy import ColumnElement, and_, or_, select

from app.auth.models import Role, User
from app.features.audit.models import LedgerEntry
from app.features.audit.schemas import LedgerEntryOut
from app.features.registration.models import Project
from app.features.registry.models import RegistryCredit, RegistryProjectAccess
from app.features.verification.models import VerificationAssignment

FULL_LEDGER_ROLES = frozenset({Role.REGISTRY_STAFF, Role.ADMIN})

# Payload fields a buyer may see: hashes, figures and references that let them trace a credit.
# Everything else (file names, emails, user IDs, free-text notes, reasons, rationales) is dropped.
BUYER_PAYLOAD_FIELDS = frozenset(
    {
        "code",
        "kind",
        "sha256",
        "size_bytes",
        "evidence_sha256",
        "area_m2",
        "vertices",
        "source",
        "other_project",
        "overlap_m2",
        "overlap_pct",
        "due_date",
        "previous_due_date",
        "serial",
        "vintage",
        "quantity",
        "status",
        "risk_rating",
        "buffer_percent",
        "buffer_quantity",
        "first_unit",
        "last_unit",
        "beneficiary",
        "reporting_year",
        "project_reference",
    }
)


def ledger_filter(user: User) -> ColumnElement[bool] | None:
    """The condition on `ledger_entries` this user may read; `None` means every entry."""
    if user.role in FULL_LEDGER_ROLES:
        return None
    project = LedgerEntry.entity == "project"
    if user.role == Role.VERIFIER:
        assigned = select(VerificationAssignment.project_id).where(
            VerificationAssignment.verifier_id == user.id
        )
        return and_(project, LedgerEntry.entity_id.in_(assigned))

    granted = select(RegistryProjectAccess.project_reference).where(
        RegistryProjectAccess.buyer_id == user.id
    )
    return or_(
        and_(
            project, LedgerEntry.entity_id.in_(select(Project.id).where(Project.code.in_(granted)))
        ),
        and_(
            LedgerEntry.entity == "credit",
            LedgerEntry.entity_id.in_(
                select(RegistryCredit.id).where(RegistryCredit.project_reference.in_(granted))
            ),
            # who else holds units of a batch is not the buyer's business
            or_(
                LedgerEntry.action != "credit.allocated",
                LedgerEntry.payload["buyer_id"].as_integer() == user.id,
            ),
        ),
        # their own access grants and revocations
        and_(
            LedgerEntry.entity == "user",
            LedgerEntry.entity_id == user.id,
            LedgerEntry.action.like("registry_access.%"),
        ),
    )


def present(entry: LedgerEntry, user: User) -> LedgerEntryOut:
    """The entry as this user may see it."""
    out = LedgerEntryOut.model_validate(entry)
    if user.role != Role.BUYER:
        return out
    payload = {k: v for k, v in entry.payload.items() if k in BUYER_PAYLOAD_FIELDS}
    return out.model_copy(update={"actor_id": None, "actor_email": None, "payload": payload})
