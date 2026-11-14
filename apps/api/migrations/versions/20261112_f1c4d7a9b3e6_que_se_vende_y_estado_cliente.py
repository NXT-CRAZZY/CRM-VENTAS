"""que_se_vende_y_estado_cliente

Reorienta el catalogo opportunity_type a "Que se vende" (Renovacion, Licencia nueva,
Usuarios adicionales, Cambio de plan, Otro sistema) y agrega opportunities.client_status
(NUEVO | EXISTENTE), calculado desde el prospecto al crear la oportunidad.

Revision ID: f1c4d7a9b3e6
Revises: e5b8c3a1f9d2
Create Date: 2026-11-12 09:00:00.000000-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'f1c4d7a9b3e6'
down_revision: str | None = 'e5b8c3a1f9d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CAT = "(SELECT id FROM catalogs WHERE code = 'opportunity_type')"

# (code, nombre, color, orden)
_NEW_OPTIONS = [
    ('USUARIOS_ADICIONALES', 'Usuarios o terminales adicionales', '#0D9488', 30),
    ('CAMBIO_PLAN', 'Cambio de plan', '#7C3AED', 40),
    ('OTRO_SISTEMA', 'Otro sistema', '#D97706', 50),
]


def upgrade() -> None:
    op.execute(
        "UPDATE catalogs SET name = 'Qué se vende', "
        "description = 'Qué se vende en la oportunidad (ya sea a un cliente nuevo o existente)' "
        "WHERE code = 'opportunity_type'"
    )
    op.execute(f"UPDATE catalog_options SET name = 'Licencia nueva', sort_order = 10 WHERE catalog_id = {_CAT} AND code = 'NUEVO'")
    op.execute(f"UPDATE catalog_options SET name = 'Renovación', sort_order = 20 WHERE catalog_id = {_CAT} AND code = 'ACTUALIZACION'")
    for code, name, color, order in _NEW_OPTIONS:
        op.execute(
            f"""
            INSERT INTO catalog_options
                (catalog_id, code, name, color, weight, is_system, sort_order, is_active, extra,
                 public_id, created_at, updated_at)
            SELECT c.id, '{code}', '{name}', '{color}', NULL, true, {order}, true, '{{}}'::jsonb,
                   gen_random_uuid(), now(), now()
            FROM catalogs c
            WHERE c.code = 'opportunity_type'
              AND NOT EXISTS (SELECT 1 FROM catalog_options o WHERE o.catalog_id = c.id AND o.code = '{code}')
            """
        )

    op.add_column(
        'opportunities',
        sa.Column('client_status', sa.String(length=20), server_default='NUEVO', nullable=False),
    )
    op.create_check_constraint(
        op.f('ck_opportunities_client_status'), 'opportunities', "client_status IN ('NUEVO','EXISTENTE')"
    )
    op.execute(
        """
        UPDATE opportunities o SET client_status = 'EXISTENTE'
        FROM prospects p
        WHERE p.id = o.prospect_id AND p.relationship_type = 'CLIENTE'
        """
    )


def downgrade() -> None:
    op.drop_constraint(op.f('ck_opportunities_client_status'), 'opportunities', type_='check')
    op.drop_column('opportunities', 'client_status')
    codes = ",".join(f"'{c}'" for c, *_ in _NEW_OPTIONS)
    op.execute(f"UPDATE opportunities SET type_id = NULL WHERE type_id IN (SELECT id FROM catalog_options WHERE catalog_id = {_CAT} AND code IN ({codes}))")
    op.execute(f"DELETE FROM catalog_options WHERE catalog_id = {_CAT} AND code IN ({codes})")
    op.execute(f"UPDATE catalog_options SET name = 'Nuevo cliente', sort_order = 20 WHERE catalog_id = {_CAT} AND code = 'NUEVO'")
    op.execute(f"UPDATE catalog_options SET name = 'Actualización', sort_order = 10 WHERE catalog_id = {_CAT} AND code = 'ACTUALIZACION'")
    op.execute("UPDATE catalogs SET name = 'Tipo comercial', description = 'Distingue ventas de actualización y de clientes nuevos' WHERE code = 'opportunity_type'")
