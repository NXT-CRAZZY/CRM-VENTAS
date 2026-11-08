"""fase_3_tareas

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-31 02:00:00.000000-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'tasks',
        sa.Column('prospect_id', sa.BigInteger(), nullable=False),
        sa.Column('opportunity_id', sa.BigInteger(), nullable=True),
        sa.Column('assignee_id', sa.BigInteger(), nullable=True),
        sa.Column('type_id', sa.BigInteger(), nullable=True),
        sa.Column('priority_id', sa.BigInteger(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('remind_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('public_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], name=op.f('fk_tasks_assignee_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['priority_id'], ['catalog_options.id'], name=op.f('fk_tasks_priority_id_catalog_options'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name=op.f('fk_tasks_prospect_id_prospects'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['type_id'], ['catalog_options.id'], name=op.f('fk_tasks_type_id_catalog_options'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tasks')),
    )
    op.create_index(op.f('ix_tasks_assignee_id'), 'tasks', ['assignee_id'], unique=False)
    op.create_index('ix_tasks_assignee_status_due', 'tasks', ['assignee_id', 'status', 'due_at'], unique=False)
    op.create_index(op.f('ix_tasks_deleted_at'), 'tasks', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_tasks_due_at'), 'tasks', ['due_at'], unique=False)
    op.create_index(op.f('ix_tasks_opportunity_id'), 'tasks', ['opportunity_id'], unique=False)
    op.create_index(op.f('ix_tasks_priority_id'), 'tasks', ['priority_id'], unique=False)
    op.create_index(op.f('ix_tasks_prospect_id'), 'tasks', ['prospect_id'], unique=False)
    op.create_index('ix_tasks_prospect_status', 'tasks', ['prospect_id', 'status'], unique=False)
    op.create_index(op.f('ix_tasks_public_id'), 'tasks', ['public_id'], unique=True)
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)
    op.create_index(op.f('ix_tasks_type_id'), 'tasks', ['type_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tasks_type_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_public_id'), table_name='tasks')
    op.drop_index('ix_tasks_prospect_status', table_name='tasks')
    op.drop_index(op.f('ix_tasks_prospect_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_priority_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_opportunity_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_due_at'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_deleted_at'), table_name='tasks')
    op.drop_index('ix_tasks_assignee_status_due', table_name='tasks')
    op.drop_index(op.f('ix_tasks_assignee_id'), table_name='tasks')
    op.drop_table('tasks')
