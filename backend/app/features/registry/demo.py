"""Explicit, idempotent demo data: python -m app.features.registry.demo.

Never called during normal startup. All references below are synthetic, not
verified credits. Requires the repository's development-only demo accounts.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.models_registry import import_all_models
from app.features.registry.models import RegistryCredit, RegistryEvidence, RegistryProjectAccess
from app.features.registry.schemas import PublicationIn
from app.features.registry.service import change_status, publish_credit


def seed_registry_demo(db: Session) -> None:
    settings = get_settings()
    if settings.app_env != "development" or not settings.seed_demo_users:
        raise RuntimeError(
            "Registry demo data is allowed only in development with demo users enabled"
        )
    users = {
        role: db.scalar(select(User).where(User.email == f"{email}@crvr.local"))
        for role, email in (("developer", "developer"), ("staff", "staff"), ("buyer", "buyer"))
    }
    if not all(users.values()):
        raise RuntimeError("Start the backend first to create the demo accounts")
    for index, (name, country, status) in enumerate(
        (
            ("Nan Reforestation", "Thailand", "active"),
            ("Chiang Mai Biochar", "Thailand", "retired"),
            ("Sabah Restoration", "Malaysia", "active"),
        ),
        start=1,
    ):
        serial = f"DEMO-{index:04d}-2026-A-00001-00100"
        if db.scalar(select(RegistryCredit.id).where(RegistryCredit.serial == serial)):
            continue
        credit = publish_credit(
            db,
            data=PublicationIn(
                serial=serial,
                project_reference=f"DEMO-{index:04d}",
                project_name=f"{name} (demo)",
                country=country,
                methodology="Synthetic demo method",
                vintage=2026,
                quantity=100,
                verifier_name="Demo verifier (fictional)",
                verification_reference=f"DEMO-VER-{index}",
                approval_reference=f"DEMO-APP-{index}",
                signed_off_at=datetime(2026, 1, 2, tzinfo=UTC),
                issued_at=datetime(2026, 2, 2, tzinfo=UTC),
            ),
            developer=users["developer"],
            actor=users["staff"],
        )
        db.add(
            RegistryEvidence(
                credit_id=credit.id,
                title="Demo verification summary",
                summary=(
                    "Synthetic buyer-safe summary for feature testing. "
                    "No real evidence or personal data."
                ),
                source_reference=f"demo-source-{index}",
                buyer_visible=True,
            )
        )
        if index < 3:
            db.add(
                RegistryProjectAccess(
                    project_reference=credit.project_reference, buyer_id=users["buyer"].id
                )
            )
        if status == "retired":
            change_status(db, credit.id, status="retired", actor=users["staff"])
    db.flush()


if __name__ == "__main__":
    import_all_models()
    with SessionLocal.begin() as session:
        seed_registry_demo(session)
    print("Synthetic registry demo records ready (three public; two permitted for the demo buyer).")
