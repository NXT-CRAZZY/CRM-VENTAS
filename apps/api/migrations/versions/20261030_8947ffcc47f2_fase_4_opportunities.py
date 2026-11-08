"""fase_4_opportunities

Revision ID: 8947ffcc47f2
Revises: b2c3d4e5f6a7
Create Date: 2026-10-30 22:54:57.326474-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '8947ffcc47f2'
down_revision: str | None = 'b2c3d4e5f6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'opportunities',
        sa.Column('prospect_id', sa.BigInteger(), nullable=False),
        sa.Column('stage_id', sa.BigInteger(), nullable=False),
        sa.Column('type_id', sa.BigInteger(), nullable=True),
        sa.Column('loss_reason_id', sa.BigInteger(), nullable=True),
        sa.Column('owner_id', sa.BigInteger(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('estimated_amount', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('probability', sa.BigInteger(), nullable=True),
        sa.Column('expected_close_date', sa.Date(), nullable=True),
        sa.Column('actual_close_date', sa.Date(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('public_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['loss_reason_id'], ['catalog_options.id'], name=op.f('fk_opportunities_loss_reason_id_catalog_options'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_opportunities_owner_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name=op.f('fk_opportunities_prospect_id_prospects'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_id'], ['catalog_options.id'], name=op.f('fk_opportunities_stage_id_catalog_options'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['type_id'], ['catalog_options.id'], name=op.f('fk_opportunities_type_id_catalog_options'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_opportunities')),
    )
    op.create_index(op.f('ix_opportunities_deleted_at'), 'opportunities', ['deleted_at'], unique=False)
    op.create_index('ix_opportunities_expected_close', 'opportunities', ['expected_close_date'], unique=False)
    op.create_index(op.f('ix_opportunities_loss_reason_id'), 'opportunities', ['loss_reason_id'], unique=False)
    op.create_index(op.f('ix_opportunities_owner_id'), 'opportunities', ['owner_id'], unique=False)
    op.create_index('ix_opportunities_owner_stage', 'opportunities', ['owner_id', 'stage_id'], unique=False)
    op.create_index(op.f('ix_opportunities_prospect_id'), 'opportunities', ['prospect_id'], unique=False)
    op.create_index('ix_opportunities_prospect_stage', 'opportunities', ['prospect_id', 'stage_id'], unique=False)
    op.create_index(op.f('ix_opportunities_public_id'), 'opportunities', ['public_id'], unique=True)
    op.create_index(op.f('ix_opportunities_stage_id'), 'opportunities', ['stage_id'], unique=False)
    op.create_index(op.f('ix_opportunities_type_id'), 'opportunities', ['type_id'], unique=False)

    # FK diferida de Fase 3: las tareas pueden estar vinculadas a una oportunidad.
    op.create_foreign_key(
        op.f('fk_tasks_opportunity_id_opportunities'),
        'tasks', 'opportunities',
        ['opportunity_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_tasks_opportunity_id_opportunities'), 'tasks', type_='foreignkey')
    op.drop_index(op.f('ix_opportunities_type_id'), table_name='opportunities')
    op.drop_index(op.f('ix_opportunities_stage_id'), table_name='opportunities')
    op.drop_index(op.f('ix_opportunities_public_id'), table_name='opportunities')
    op.drop_index('ix_opportunities_prospect_stage', table_name='opportunities')
    op.drop_index(op.f('ix_opportunities_prospect_id'), table_name='opportunities')
    op.drop_index('ix_opportunities_owner_stage', table_name='opportunities')
    op.drop_index(op.f('ix_opportunities_owner_id'), table_name='opportunities')
    op.drop_index(op.f('ix_opportunities_loss_reason_id'), table_name='opportunities')
    op.drop_index('ix_opportunities_expected_close', table_name='opportunities')
    op.drop_index(op.f('ix_opportunities_deleted_at'), table_name='opportunities')
    op.drop_table('opportunities')
