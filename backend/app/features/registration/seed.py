"""Demo projects for local development (names and IDs from the UI mock-up)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.features.registration.models import Project

ADDITIONALITY = (
    "Without carbon finance the land would stay as it is: restoration costs exceed any income "
    "from the site, no regulation requires it, and no comparable project exists in the district."
)

DEMO_PROJECTS: list[dict[str, Any]] = [
    {
        "code": "CRVR-0088",
        "name": "Nan Valley Community Forest",
        "owner": "developer2@crvr.local",
        "status": "issued",
        "registered": "2025-11-12",
        "methodology": "VM0047",
        "period": (2025, 2045),
        "area_ha": 860,
        "est_removal_tco2e": 15200,
        "baseline": "Secondary forest degraded by shifting cultivation; 21 tC/ha in 2025.",
    },
    {
        "code": "CRVR-0092",
        "name": "Phrae Agroforestry",
        "owner": "developer2@crvr.local",
        "status": "verified",
        "registered": "2026-03-03",
        "methodology": "VM0042",
        "period": (2026, 2046),
        "area_ha": 610,
        "est_removal_tco2e": 9100,
        "baseline": "Maize monoculture with residue burning; soil organic carbon 1.1%.",
    },
    {
        "code": "CRVR-0131",
        "name": "Chiang Rai Mangrove Restore",
        "owner": "developer@crvr.local",
        "status": "verified",
        "registered": "2026-08-04",
        "methodology": "VM0033",
        "period": (2026, 2056),
        "area_ha": 340,
        "est_removal_tco2e": 18400,
        "baseline": "Abandoned shrimp ponds, no mangrove regrowth since 2012.",
    },
    {
        "code": "CRVR-0147",
        "name": "Nan Reforestation Phase II",
        "owner": "developer@crvr.local",
        "status": "submitted",
        "registered": "2026-09-12",
        "methodology": "VM0047",
        "period": (2027, 2047),
        "area_ha": 1240,
        "est_removal_tco2e": 24800,
        "baseline": (
            "Degraded grazing land, no natural regeneration recorded 2019–2026. Baseline stock "
            "8.4 tC/ha from the 2026 field survey."
        ),
    },
    {
        "code": "CRVR-0156",
        "name": "Phetchabun Agroforestry",
        "owner": "developer@crvr.local",
        "status": "draft",
        "registered": "2026-10-01",
        "methodology": "VM0042",
        "period": None,
        "area_ha": None,
        "est_removal_tco2e": None,
        "baseline": None,
    },
]


def _registration_fields(data: dict[str, Any]) -> dict[str, Any]:
    start, end = data["period"] or (None, None)
    registered = datetime.fromisoformat(data["registered"]).replace(tzinfo=UTC)
    return {
        "methodology": data["methodology"],
        "crediting_start_year": start,
        "crediting_end_year": end,
        "area_ha": data["area_ha"],
        "est_removal_tco2e": data["est_removal_tco2e"],
        "baseline_summary": data["baseline"],
        "additionality_reasoning": ADDITIONALITY if data["status"] != "draft" else None,
        "submitted_at": registered if data["status"] != "draft" else None,
    }


def seed_demo_projects(db: Session) -> int:
    created = 0
    for data in DEMO_PROJECTS:
        existing = db.scalar(select(Project).where(Project.code == data["code"]))
        if existing is not None:
            # Databases seeded before F1 had only the stub columns — fill them in once
            if existing.methodology is None:
                for field, value in _registration_fields(data).items():
                    setattr(existing, field, value)
            continue
        owner = db.scalar(select(User).where(User.email == data["owner"]))
        if owner is None:
            continue
        db.add(
            Project(
                code=data["code"],
                name=data["name"],
                owner_id=owner.id,
                status=data["status"],
                created_at=datetime.fromisoformat(data["registered"]).replace(tzinfo=UTC),
                **_registration_fields(data),
            )
        )
        created += 1
    db.commit()
    return created
