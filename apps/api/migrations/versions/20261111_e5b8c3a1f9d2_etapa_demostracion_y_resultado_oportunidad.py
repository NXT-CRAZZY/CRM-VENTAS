"""etapa_demostracion_y_resultado_oportunidad

Agrega la etapa DEMOSTRACION (antes de COTIZACION), deja de usar NEGOCIACION y
vincula cada interaccion con la oportunidad que creo/movio (interactions.opportunity_id).

Revision ID: e5b8c3a1f9d2
Revises: d7a2b5c8e1f4
Create Date: 2026-11-11 17:00:00.000000-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'e5b8c3a1f9d2'
down_revision: str | None = 'd7a2b5c8e1f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STAGE_CATALOG = "(SELECT id FROM catalogs WHERE code = 'pipeline_stage')"


def upgrade() -> None:
    # Nueva etapa DEMOSTRACION entre NUEVO y COTIZACION.
    op.execute(
        f"""
        INSERT INTO catalog_options
            (catalog_id, code, name, color, weight, is_system, sort_order, is_active, extra,
             public_id, created_at, updated_at)
        SELECT c.id, 'DEMOSTRACION', 'Demostración', '#7C3AED', 15, true, 15, true, '{{}}'::jsonb,
               gen_random_uuid(), now(), now()
        FROM catalogs c
        WHERE c.code = 'pipeline_stage'
          AND NOT EXISTS (
            SELECT 1 FROM catalog_options o WHERE o.catalog_id = c.id AND o.code = 'DEMOSTRACION'
          )
        """
    )
    op.execute(
        f"""
        UPDATE catalog_options SET sort_order = CASE code
            WHEN 'NUEVO' THEN 10 WHEN 'DEMOSTRACION' THEN 20 WHEN 'COTIZACION' THEN 30
            WHEN 'CERRADO_GANADO' THEN 40 WHEN 'CERRADO_PERDIDO' THEN 50 ELSE sort_order END
        WHERE catalog_id = {_STAGE_CATALOG}
          AND code IN ('NUEVO','DEMOSTRACION','COTIZACION','CERRADO_GANADO','CERRADO_PERDIDO')
        """
    )

    # Las oportunidades en NEGOCIACION pasan a COTIZACION y la etapa se desactiva.
    op.execute(
        f"""
        UPDATE opportunities
        SET stage_id = (SELECT id FROM catalog_options WHERE catalog_id = {_STAGE_CATALOG} AND code = 'COTIZACION')
        WHERE stage_id = (SELECT id FROM catalog_options WHERE catalog_id = {_STAGE_CATALOG} AND code = 'NEGOCIACION')
        """
    )
    op.execute(
        f"""
        UPDATE catalog_options SET is_active = false, is_system = false
        WHERE catalog_id = {_STAGE_CATALOG} AND code = 'NEGOCIACION'
        """
    )

    op.add_column('interactions', sa.Column('opportunity_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f('fk_interactions_opportunity_id_opportunities'),
        'interactions', 'opportunities', ['opportunity_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(op.f('ix_interactions_opportunity_id'), 'interactions', ['opportunity_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_interactions_opportunity_id'), table_name='interactions')
    op.drop_constraint(op.f('fk_interactions_opportunity_id_opportunities'), 'interactions', type_='foreignkey')
    op.drop_column('interactions', 'opportunity_id')
    op.execute(
        f"""
        UPDATE catalog_options SET is_active = true, is_system = true
        WHERE catalog_id = {_STAGE_CATALOG} AND code = 'NEGOCIACION'
        """
    )
    op.execute(
        f"""
        UPDATE opportunities
        SET stage_id = (SELECT id FROM catalog_options WHERE catalog_id = {_STAGE_CATALOG} AND code = 'NUEVO')
        WHERE stage_id = (SELECT id FROM catalog_options WHERE catalog_id = {_STAGE_CATALOG} AND code = 'DEMOSTRACION')
        """
    )
    op.execute(
        f"DELETE FROM catalog_options WHERE catalog_id = {_STAGE_CATALOG} AND code = 'DEMOSTRACION'"
    )
