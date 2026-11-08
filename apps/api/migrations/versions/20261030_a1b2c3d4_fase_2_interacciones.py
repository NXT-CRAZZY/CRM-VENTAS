"""fase_2_interacciones

Revision ID: a1b2c3d4e5f6
Revises: 15935b0bb612
Create Date: 2026-10-30 15:00:00.000000-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '15935b0bb612'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'interactions',
        sa.Column('prospect_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('contact_id', sa.BigInteger(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('mode_id', sa.BigInteger(), nullable=True),
        sa.Column('result_id', sa.BigInteger(), nullable=False),
        sa.Column('interest_level_id', sa.BigInteger(), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('next_action_desc', sa.String(length=200), nullable=True),
        sa.Column('next_action_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stage_before', sa.String(length=20), nullable=True),
        sa.Column('stage_after', sa.String(length=20), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('public_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['catalog_options.id'], name=op.f('fk_interactions_channel_id_catalog_options'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['contact_id'], ['prospect_contacts.id'], name=op.f('fk_interactions_contact_id_prospect_contacts'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['interest_level_id'], ['catalog_options.id'], name=op.f('fk_interactions_interest_level_id_catalog_options'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['mode_id'], ['catalog_options.id'], name=op.f('fk_interactions_mode_id_catalog_options'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name=op.f('fk_interactions_prospect_id_prospects'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['result_id'], ['catalog_options.id'], name=op.f('fk_interactions_result_id_catalog_options'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_interactions_user_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_interactions')),
    )
    op.create_index(op.f('ix_interactions_contact_id'), 'interactions', ['contact_id'], unique=False)
    op.create_index(op.f('ix_interactions_channel_id'), 'interactions', ['channel_id'], unique=False)
    op.create_index(op.f('ix_interactions_deleted_at'), 'interactions', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_interactions_interest_level_id'), 'interactions', ['interest_level_id'], unique=False)
    op.create_index(op.f('ix_interactions_mode_id'), 'interactions', ['mode_id'], unique=False)
    op.create_index('ix_interactions_next_action', 'interactions', ['next_action_at'], unique=False)
    op.create_index(op.f('ix_interactions_occurred_at'), 'interactions', ['occurred_at'], unique=False)
    op.create_index(op.f('ix_interactions_prospect_id'), 'interactions', ['prospect_id'], unique=False)
    op.create_index('ix_interactions_prospect_occurred', 'interactions', ['prospect_id', 'occurred_at'], unique=False)
    op.create_index(op.f('ix_interactions_public_id'), 'interactions', ['public_id'], unique=True)
    op.create_index(op.f('ix_interactions_result_id'), 'interactions', ['result_id'], unique=False)
    op.create_index(op.f('ix_interactions_user_id'), 'interactions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_interactions_user_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_result_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_public_id'), table_name='interactions')
    op.drop_index('ix_interactions_prospect_occurred', table_name='interactions')
    op.drop_index(op.f('ix_interactions_prospect_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_occurred_at'), table_name='interactions')
    op.drop_index('ix_interactions_next_action', table_name='interactions')
    op.drop_index(op.f('ix_interactions_mode_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_interest_level_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_deleted_at'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_channel_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_contact_id'), table_name='interactions')
    op.drop_table('interactions')
