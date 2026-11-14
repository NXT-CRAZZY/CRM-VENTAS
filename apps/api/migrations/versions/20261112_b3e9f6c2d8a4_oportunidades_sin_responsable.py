"""oportunidades_sin_responsable

Asigna responsable a las oportunidades que no lo tienen (el del prospecto) para que
sean visibles en el Pipeline de quien las creo.

Revision ID: b3e9f6c2d8a4
Revises: a2d8e5b1c7f3
Create Date: 2026-11-12 11:00:00.000000-05:00
"""
from collections.abc import Sequence

from alembic import op


revision: str = 'b3e9f6c2d8a4'
down_revision: str | None = 'a2d8e5b1c7f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE opportunities o SET owner_id = p.owner_id
        FROM prospects p
        WHERE p.id = o.prospect_id AND o.owner_id IS NULL AND p.owner_id IS NOT NULL
        """
    )


def downgrade() -> None:
    pass
