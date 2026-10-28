"""Demo boundaries near Nan, Thailand, reproducing the mock-up's Map screen.

Shapes are the mock-up's polygons scaled to real size: CRVR-0147 is 1,240 ha and its south-east
corner overlaps CRVR-0092 by 3.1% (above the 0.5% tolerance, so it is flagged). CRVR-0088 touches
CRVR-0147's northern edge without overlapping. CRVR-0156 is left without a boundary to draw.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.features.boundary import service
from app.features.boundary.models import BoundarySource
from app.features.registration.models import Project


def _polygon(ring: list[list[float]]) -> dict:
    return {"type": "Polygon", "coordinates": [ring]}


# Registered first, so the later CRVR-0147 is the one flagged for overlapping them.
DEMO_BOUNDARIES = [
    (
        "CRVR-0088",
        _polygon(
            [
                [100.76114, 18.789856],
                [100.757803, 18.805759],
                [100.784508, 18.80894],
                [100.787843, 18.794733],
                [100.76114, 18.789856],
            ]
        ),
    ),
    (
        "CRVR-0092",
        _polygon(
            [
                [100.789716, 18.762928],
                [100.797727, 18.780315],
                [100.813749, 18.776498],
                [100.809744, 18.759535],
                [100.789716, 18.762928],
            ]
        ),
    ),
    (
        "CRVR-0131",
        _polygon(
            [
                [99.85, 19.9],
                [99.8675, 19.9],
                [99.8675, 19.9175],
                [99.85, 19.9175],
                [99.85, 19.9],
            ]
        ),
    ),
    (
        "CRVR-0147",
        _polygon(
            [
                [100.76114, 18.789856],
                [100.787843, 18.794733],
                [100.799637, 18.780315],
                [100.791626, 18.762928],
                [100.766258, 18.760171],
                [100.757802, 18.776074],
                [100.76114, 18.789856],
            ]
        ),
    ),
]


def seed_demo_boundaries(db: Session) -> int:
    admin = db.scalar(select(User).where(User.role == Role.ADMIN).order_by(User.id))
    created = 0
    for code, geometry in DEMO_BOUNDARIES:
        project = db.scalar(select(Project).where(Project.code == code))
        if project is None or admin is None or service.get_boundary(db, project.id):
            continue
        owner = db.get(User, project.owner_id)
        service.save_boundary(db, project, geometry, BoundarySource.DRAWN, owner or admin)
        created += 1
    return created
