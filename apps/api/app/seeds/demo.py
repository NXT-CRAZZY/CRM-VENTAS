"""Datos de demostración inventados — SOLO para desarrollo.

Fase 1 crea el equipo comercial ficticio. En fases siguientes este mismo comando
irá agregando prospectos, seguimientos, cotizaciones y ventas de ejemplo.

Uso:  python -m app.seeds.demo
"""

import sys

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.core.models_registry  # noqa: F401
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.modules.rbac.infrastructure.models import Role
from app.modules.users.infrastructure.models import User
from app.seeds.base import run_base_seed

log = structlog.get_logger()

DEMO_PASSWORD = "Demo1234"

# (correo, nombre, teléfono, rol)
DEMO_USERS = [
    ("gerencia@dataservice.pe", "Ricardo Salazar Paredes", "987 654 321", "MANAGER"),
    ("maria.quispe@dataservice.pe", "María Quispe Huamán", "954 112 233", "SALES"),
    ("lucia.fernandez@dataservice.pe", "Lucía Fernández Rojas", "945 778 899", "SALES"),
    ("carla.rojas@dataservice.pe", "Carla Rojas Villanueva", "962 334 455", "SALES"),
]


def seed_demo_users(s: Session) -> None:
    roles = {r.code: r for r in s.scalars(select(Role))}
    password_hash = hash_password(DEMO_PASSWORD)
    for email, name, phone, role_code in DEMO_USERS:
        if s.scalar(select(User.id).where(User.email == email)):
            continue
        s.add(User(email=email, full_name=name, phone=phone, password_hash=password_hash, roles=[roles[role_code]]))
    s.flush()


def main() -> None:
    configure_logging()
    if get_settings().is_production:
        log.error("seed_demo_blocked", reason="No se cargan datos demo en producción")
        sys.exit(1)
    with SessionLocal() as session, session.begin():
        run_base_seed(session)
        seed_demo_users(session)
    log.info("seed_demo_done", password=DEMO_PASSWORD, users=[u[0] for u in DEMO_USERS])


if __name__ == "__main__":
    main()
