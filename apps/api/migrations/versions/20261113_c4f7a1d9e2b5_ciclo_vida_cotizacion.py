"""ciclo_vida_cotizacion

Fechas de envio/aceptacion/rechazo, motivo de rechazo y vinculo tarea-cotizacion.

Revision ID: c4f7a1d9e2b5
Revises: b3e9f6c2d8a4
Create Date: 2026-11-13 10:00:00.000000-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'c4f7a1d9e2b5'
down_revision: str | None = 'b3e9f6c2d8a4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('quotes', sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quotes', sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quotes', sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quotes', sa.Column('reject_reason_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_quotes_reject_reason_id', 'quotes', 'catalog_options', ['reject_reason_id'], ['id'], ondelete='SET NULL'
    )
    op.add_column('tasks', sa.Column('quote_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_tasks_quote_id', 'tasks', 'quotes', ['quote_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_tasks_quote_id', 'tasks', ['quote_id'])
    # Cotizaciones ya existentes: aproximar las fechas con la ultima actualizacion.
    op.execute("UPDATE quotes SET sent_at = updated_at WHERE status IN ('SENT','ACCEPTED','REJECTED')")
    op.execute("UPDATE quotes SET accepted_at = updated_at WHERE status = 'ACCEPTED'")
    op.execute("UPDATE quotes SET rejected_at = updated_at WHERE status = 'REJECTED'")


def downgrade() -> None:
    op.drop_index('ix_tasks_quote_id', table_name='tasks')
    op.drop_constraint('fk_tasks_quote_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'quote_id')
    op.drop_constraint('fk_quotes_reject_reason_id', 'quotes', type_='foreignkey')
    op.drop_column('quotes', 'reject_reason_id')
    op.drop_column('quotes', 'rejected_at')
    op.drop_column('quotes', 'accepted_at')
    op.drop_column('quotes', 'sent_at')
