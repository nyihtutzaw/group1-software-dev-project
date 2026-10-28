"""Test setup: a real PostGIS database (crvr_test), migrated once, rolled back after every test."""

import os

# Point the app at the test database *before* anything imports app settings.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://crvr:crvr@localhost:5432/crvr_test"
)

from collections.abc import Callable, Iterator  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth.models import Role, User  # noqa: E402
from app.core.db import engine, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.features.registration.models import Project  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "test-password"


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = os.environ["DATABASE_URL"]
    command.upgrade(cfg, "head")


@pytest.fixture
def db() -> Iterator[Session]:
    """A session whose changes are rolled back when the test ends."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    def _make(role: Role = Role.DEVELOPER, email: str | None = None) -> User:
        user = User(
            email=email or f"{role.value}@test.local",
            full_name=f"Test {role.value}",
            role=role,
            password_hash=hash_password(PASSWORD),
        )
        db.add(user)
        db.flush()
        return user

    return _make


@pytest.fixture
def login(client: TestClient, make_user: Callable[..., User]) -> Callable[[Role], User]:
    """Create a user with the given role and sign the test client in as them."""

    def _login(role: Role) -> User:
        user = make_user(role)
        res = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
        assert res.status_code == 200, res.text
        return user

    return _login


@pytest.fixture
def make_project(db: Session, make_user: Callable[..., User]) -> Callable[..., Project]:
    """Create a project; owned by a new developer unless `owner` is given."""
    counter = iter(range(9000, 10000))

    def _make(owner: User | None = None, name: str = "Test project") -> Project:
        n = next(counter)
        if owner is None:
            owner = make_user(Role.DEVELOPER, email=f"owner{n}@test.local")
        project = Project(code=f"CRVR-{n}", name=name, owner_id=owner.id)
        db.add(project)
        db.flush()
        return project

    return _make
