---
name: backend-code
description: Write CRVR backend code the project's way — FastAPI feature modules, SQLAlchemy 2 models with PostGIS geometry, Alembic migrations, role checks with require_roles, and pytest tests against the real test database. Use for any change under backend/.
---

# Backend code

Python 3.13 · FastAPI · SQLAlchemy 2.x (**sync** sessions) · GeoAlchemy2 · Alembic · pytest · ruff.

## Where things go

Each feature is a package in `backend/app/features/<name>/` (`registration`=F1, `boundary`=F2,
`verification`=F3, `registry`=F4, `audit`=F5):

| File | Contains |
|---|---|
| `router.py` | `router = APIRouter(prefix="/…")` — thin HTTP layer: parse, call service, return |
| `models.py` | ORM tables (subclass `app.core.db.Base`) — found automatically by Alembic |
| `schemas.py` | Pydantic request/response models (`…In`, `…Out`, `model_config = ConfigDict(from_attributes=True)`) |
| `service.py` | Business logic as plain functions taking `db: Session` — the part you test hardest |

Routers are already mounted in `app/main.py` under `/api`. A new feature package needs one
`api.include_router(...)` line there.

Shared code: `app/core/` (config, db, security), `app/auth/` (User, Role, `get_current_user`,
`require_roles`). Change it only when needed and mention it in the commit/PR.

## Patterns

```python
# router.py
@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DEVELOPER)),
) -> Project:
    return service.create_project(db, owner=user, data=body)


# service.py — raise HTTPException for expected failures, commit here
def create_project(db: Session, owner: User, data: ProjectIn) -> Project:
    project = Project(owner_id=owner.id, **data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# models.py — SQLAlchemy 2 typed style
class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(200))
```

- Queries: `db.scalar(select(X).where(...))`, `db.scalars(select(X)).all()` — not legacy `db.query`.
- Authorisation: every non-public route uses `require_roles(...)` (or `get_current_user` and an
  explicit ownership check). Developers may only see their own projects.
- **Separation of duties (FR-10):** the user who submits/makes a record can never approve it —
  check `approver.id != record.created_by_id` in the service and test it.
- **Audit (F5):** critical actions (submit, boundary change, verification decision, approval,
  issuance) must be written to the ledger once F5 provides the function; until then leave a
  clearly named call site, e.g. a `record_action(...)` stub agreed with F5.
- Evidence files are write-once: never update or delete a stored file; store under
  `settings.storage_dir`.
- Settings come from `app.core.config.get_settings()` — add new env vars there, in
  `docker-compose.yml` and `.env.example`.

## PostGIS (F2 and anything spatial)

```python
from geoalchemy2 import Geometry
boundary: Mapped[str] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))

# overlap in the database, not in Python
from sqlalchemy import func
stmt = select(Boundary.project_id, func.ST_Area(func.ST_Intersection(Boundary.geom, new_geom).cast(Geography)))
```

Store WGS 84 (SRID 4326); compute areas with `geography` casts (square metres).

## Migrations

After changing a model:

```bash
docker compose exec backend alembic revision --autogenerate -m "add projects table"
# open the new file in migrations/versions/ and READ it — autogenerate is a draft
docker compose exec backend alembic upgrade head
docker compose exec backend alembic check        # "No new upgrade operations detected."
```

One migration per logical change, committed together with the model. Never edit a migration that
is already on `main` — add a new one.

## Tests

`backend/tests/`, one file per area (`test_<feature>_<thing>.py`). The fixtures in `conftest.py`
give you a real migrated PostGIS database that is rolled back after each test:

- `client` — FastAPI TestClient
- `db` — the session the app uses during the test
- `make_user(role)` — create a user · `login(role)` — create one and sign the client in

```python
def test_developer_cannot_approve_own_project(client, login, db):
    user = login(Role.DEVELOPER)
    ...
    assert client.post(f"/api/projects/{p.id}/approve").status_code == 403
```

Test the role rules and every acceptance criterion in the feature doc. Run with
`docker compose exec backend pytest`.

## Style

`ruff format` + `ruff check` (config in `pyproject.toml`, line length 100). Type-hint every
function. Docstrings for anything non-obvious; comments explain *why*.
