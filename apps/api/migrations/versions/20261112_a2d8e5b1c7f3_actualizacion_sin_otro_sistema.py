"""actualizacion_sin_otro_sistema

Renombra "Renovación" a "Actualización" (jerga de la empresa) y elimina la opción "Otro sistema".

Revision ID: a2d8e5b1c7f3
Revises: f1c4d7a9b3e6
Create Date: 2026-11-12 10:00:00.000000-05:00
"""
from collections.abc import Sequence

from alembic import op


revision: str = 'a2d8e5b1c7f3'
down_revision: str | None = 'f1c4d7a9b3e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CAT = "(SELECT id FROM catalogs WHERE code = 'opportunity_type')"


def upgrade() -> None:
    op.execute(f"UPDATE catalog_options SET name = 'Actualización' WHERE catalog_id = {_CAT} AND code = 'ACTUALIZACION'")
    op.execute(
        f"UPDATE opportunities SET type_id = NULL WHERE type_id IN "
        f"(SELECT id FROM catalog_options WHERE catalog_id = {_CAT} AND code = 'OTRO_SISTEMA')"
    )
    op.execute(f"DELETE FROM catalog_options WHERE catalog_id = {_CAT} AND code = 'OTRO_SISTEMA'")


def downgrade() -> None:
    op.execute(f"UPDATE catalog_options SET name = 'Renovación' WHERE catalog_id = {_CAT} AND code = 'ACTUALIZACION'")
    op.execute(
        f"""
        INSERT INTO catalog_options
            (catalog_id, code, name, color, weight, is_system, sort_order, is_active, extra,
             public_id, created_at, updated_at)
        SELECT c.id, 'OTRO_SISTEMA', 'Otro sistema', '#D97706', NULL, true, 50, true, '{{}}'::jsonb,
               gen_random_uuid(), now(), now()
        FROM catalogs c
        WHERE c.code = 'opportunity_type'
          AND NOT EXISTS (SELECT 1 FROM catalog_options o WHERE o.catalog_id = c.id AND o.code = 'OTRO_SISTEMA')
        """
    )
