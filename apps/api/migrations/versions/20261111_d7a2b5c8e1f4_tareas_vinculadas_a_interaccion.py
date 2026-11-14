"""tareas_vinculadas_a_interaccion

Agrega tasks.interaction_id para vincular la "próxima acción" a su interacción.

Revision ID: d7a2b5c8e1f4
Revises: c4f1a9d2e7b3
Create Date: 2026-11-11 15:00:00.000000-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd7a2b5c8e1f4'
down_revision: str | None = 'c4f1a9d2e7b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('interaction_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f('fk_tasks_interaction_id_interactions'),
        'tasks', 'interactions', ['interaction_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(op.f('ix_tasks_interaction_id'), 'tasks', ['interaction_id'], unique=False)

    # Enlaza las tareas migradas desde próximas acciones con su interacción de origen
    # (misma persona, misma fecha) cuando la coincidencia es única.
    op.execute(
        """
        UPDATE tasks t
        SET interaction_id = i.id
        FROM interactions i
        WHERE t.interaction_id IS NULL
          AND t.deleted_at IS NULL
          AND i.deleted_at IS NULL
          AND i.prospect_id = t.prospect_id
          AND i.next_action_at IS NOT NULL
          AND i.next_action_at = t.due_at
          AND (
              SELECT COUNT(*) FROM interactions i2
              WHERE i2.deleted_at IS NULL
                AND i2.prospect_id = t.prospect_id
                AND i2.next_action_at = t.due_at
          ) = 1
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_tasks_interaction_id'), table_name='tasks')
    op.drop_constraint(op.f('fk_tasks_interaction_id_interactions'), 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'interaction_id')
