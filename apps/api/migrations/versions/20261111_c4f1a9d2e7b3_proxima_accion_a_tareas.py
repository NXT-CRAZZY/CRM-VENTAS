"""proxima_accion_a_tareas

Convierte las "próximas acciones" guardadas en prospectos en tareas reales.

Revision ID: c4f1a9d2e7b3
Revises: 8db7cf0cfc84
Create Date: 2026-11-11 12:00:00.000000-05:00
"""
from collections.abc import Sequence

from alembic import op


revision: str = 'c4f1a9d2e7b3'
down_revision: str | None = '8db7cf0cfc84'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Cada próxima acción vigente del prospecto pasa a ser una tarea pendiente
    # asignada a su responsable (si no existe ya una tarea equivalente).
    op.execute(
        """
        INSERT INTO tasks (public_id, prospect_id, assignee_id, title, due_at, status)
        SELECT gen_random_uuid(), p.id, p.owner_id,
               LEFT(COALESCE(NULLIF(TRIM(p.next_action_desc), ''), 'Próxima acción'), 200),
               p.next_action_at, 'PENDING'
        FROM prospects p
        WHERE p.deleted_at IS NULL
          AND p.next_action_at IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM tasks t
              WHERE t.prospect_id = p.id
                AND t.deleted_at IS NULL
                AND t.due_at = p.next_action_at
          )
        """
    )
    op.execute(
        """
        UPDATE prospects
        SET next_action_at = NULL, next_action_desc = NULL
        WHERE next_action_at IS NOT NULL OR next_action_desc IS NOT NULL
        """
    )


def downgrade() -> None:
    # Las tareas creadas no se revierten: ya forman parte del flujo normal de Tareas.
    pass
