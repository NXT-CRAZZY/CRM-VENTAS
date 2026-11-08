import os

# Debe configurarse antes de importar la aplicación.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://crm:crm@localhost:5432/crm_test")

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.db import engine, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.rbac.infrastructure.models import Role  # noqa: E402
from app.modules.users.infrastructure.models import User  # noqa: E402
from app.seeds.base import run_base_seed  # noqa: E402

API = "/api/v1"
ADMIN_EMAIL = "admin@dataservice.pe"
ADMIN_PASSWORD = "Admin123!"
PASSWORD = "Clave1234"


@pytest.fixture(scope="session", autouse=True)
def _database() -> Iterator[None]:
    """Migra la BD de pruebas desde cero (valida también las migraciones) y carga el seed base."""
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with Session(engine) as s, s.begin():
        run_base_seed(s)
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    """Cada test corre dentro de una transacción que se revierte al final."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def _get_db() -> Iterator[Session]:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db: Session, email: str, role_code: str, password: str = PASSWORD, name: str | None = None) -> User:
    role = db.scalar(select(Role).where(Role.code == role_code))
    user = User(
        email=email, full_name=name or email.split("@")[0].title(), password_hash=hash_password(password), roles=[role]
    )
    db.add(user)
    db.flush()
    return user


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    return login(client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def sales_user(db: Session) -> User:
    return make_user(db, "vendedora@test.pe", "SALES", name="Vendedora Test")


@pytest.fixture
def sales_headers(client: TestClient, sales_user: User) -> dict[str, str]:
    return login(client, sales_user.email)


@pytest.fixture
def manager_headers(client: TestClient, db: Session) -> dict[str, str]:
    make_user(db, "gerente@test.pe", "MANAGER")
    return login(client, "gerente@test.pe")
