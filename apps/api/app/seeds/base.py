"""Seed obligatorio (también en producción). Es idempotente: nunca sobrescribe datos
editados por los usuarios; solo crea lo que falta.

Uso:  python -m app.seeds.base
"""

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.core.models_registry  # noqa: F401
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.products.infrastructure.models import Product, ProductCategory
from app.modules.rbac.domain.permissions import ALL_CODES, PERMISSIONS, SYSTEM_ROLES
from app.modules.rbac.infrastructure.models import Permission, Role
from app.modules.users.infrastructure.models import User
from app.seeds.data.catalogs import CATALOGS
from app.seeds.data.products import CATEGORIES, PRODUCTS_PARSED

log = structlog.get_logger()


def seed_permissions_and_roles(s: Session) -> None:
    existing = {p.code: p for p in s.scalars(select(Permission))}
    for definition in PERMISSIONS:
        perm = existing.get(definition.code)
        if perm is None:
            perm = Permission(code=definition.code, module=definition.module, name=definition.name)
            s.add(perm)
            existing[definition.code] = perm
        else:
            perm.module, perm.name = definition.module, definition.name
    s.flush()

    for code, name, description, perm_codes in SYSTEM_ROLES:
        role = s.scalar(select(Role).where(Role.code == code))
        if role is None:
            role = Role(code=code, name=name, description=description, is_system=True)
            role.permissions = [existing[c] for c in perm_codes]
            s.add(role)
        elif code == "ADMIN":
            # El administrador siempre recibe los permisos nuevos que se registren.
            role.permissions = [existing[c] for c in ALL_CODES]
    s.flush()


def seed_catalogs(s: Session) -> None:
    for code, name, description, uses_color, uses_weight, options in CATALOGS:
        catalog = s.scalar(select(Catalog).where(Catalog.code == code))
        if catalog is None:
            catalog = Catalog(
                code=code, name=name, description=description, uses_color=uses_color, uses_weight=uses_weight
            )
            s.add(catalog)
            s.flush()
        present = set(s.scalars(select(CatalogOption.code).where(CatalogOption.catalog_id == catalog.id)))
        for index, (opt_code, opt_name, legacy, color, weight, is_system) in enumerate(options):
            if opt_code in present:
                continue
            s.add(
                CatalogOption(
                    catalog_id=catalog.id,
                    code=opt_code,
                    name=opt_name,
                    legacy_code=legacy,
                    color=color,
                    weight=weight,
                    is_system=is_system,
                    sort_order=(index + 1) * 10,
                    is_active=True,
                    extra={},
                )
            )
    s.flush()


def seed_products(s: Session) -> None:
    categories = {c.code: c for c in s.scalars(select(ProductCategory))}
    for code, name, line, order in CATEGORIES:
        if code not in categories:
            categories[code] = ProductCategory(code=code, name=name, product_line=line, sort_order=order)
            s.add(categories[code])
    s.flush()

    present = set(s.scalars(select(Product.code)))
    for code, name, category_code, kind, billing, price in PRODUCTS_PARSED:
        if code in present:
            continue
        s.add(
            Product(
                code=code,
                name=name,
                category_id=categories[category_code].id,
                kind=kind,
                billing_period=billing,
                list_price=price,
                is_active=True,
            )
        )
    s.flush()


def seed_admin(s: Session) -> None:
    settings = get_settings()
    admin_role = s.scalar(select(Role).where(Role.code == "ADMIN"))
    has_admin = s.scalar(select(User.id).join(User.roles).where(Role.code == "ADMIN").limit(1))
    if has_admin or admin_role is None:
        return
    s.add(
        User(
            email=settings.initial_admin_email.lower(),
            full_name=settings.initial_admin_name,
            password_hash=hash_password(settings.initial_admin_password.get_secret_value()),
            must_change_password=settings.is_production,
            roles=[admin_role],
        )
    )
    s.flush()
    log.info("seed_admin_created", email=settings.initial_admin_email)


def run_base_seed(s: Session) -> None:
    seed_permissions_and_roles(s)
    seed_catalogs(s)
    seed_products(s)
    seed_admin(s)


def main() -> None:
    configure_logging()
    with SessionLocal() as session, session.begin():
        run_base_seed(session)
    log.info("seed_base_done")


if __name__ == "__main__":
    main()
