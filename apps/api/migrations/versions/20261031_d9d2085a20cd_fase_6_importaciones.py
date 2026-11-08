"""fase_6_importaciones

Revision ID: d9d2085a20cd
Revises: feaa88c4bfc2
Create Date: 2026-10-31 07:45:00.000000-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'd9d2085a20cd'
down_revision: str | None = 'feaa88c4bfc2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'import_jobs',
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('sheet_name', sa.String(length=120), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('processed_rows', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_prospects', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('updated_prospects', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_interactions', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_opportunities', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_by_id', sa.BigInteger(), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('public_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_import_jobs_created_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_import_jobs'))
    )
    op.create_index(op.f('ix_import_jobs_created_by_status'), 'import_jobs', ['created_by_id', 'status'], unique=False)
    op.create_index(op.f('ix_import_jobs_status'), 'import_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_import_jobs_public_id'), 'import_jobs', ['public_id'], unique=True)

    op.create_table(
        'import_row_errors',
        sa.Column('import_job_id', sa.BigInteger(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('field', sa.String(length=60), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('public_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['import_job_id'], ['import_jobs.id'], name=op.f('fk_import_row_errors_import_job_id_import_jobs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_import_row_errors'))
    )
    op.create_index(op.f('ix_import_row_errors_import_job_id'), 'import_row_errors', ['import_job_id'], unique=False)
    op.create_index(op.f('ix_import_row_errors_public_id'), 'import_row_errors', ['public_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_import_row_errors_public_id'), table_name='import_row_errors')
    op.drop_index(op.f('ix_import_row_errors_import_job_id'), table_name='import_row_errors')
    op.drop_table('import_row_errors')
    op.drop_index(op.f('ix_import_jobs_public_id'), table_name='import_jobs')
    op.drop_index(op.f('ix_import_jobs_status'), table_name='import_jobs')
    op.drop_index(op.f('ix_import_jobs_created_by_status'), table_name='import_jobs')
    op.drop_table('import_jobs')
