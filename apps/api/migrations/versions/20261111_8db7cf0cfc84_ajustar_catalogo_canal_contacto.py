"""ajustar_catalogo_canal_contacto

Revision ID: 8db7cf0cfc84
Revises: 18b1689f20f5
Create Date: 2026-11-11 09:49:55.290186-05:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '8db7cf0cfc84'
down_revision: str | None = '18b1689f20f5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Renombrar el catálogo de "Forma de contacto" a "Canal de contacto"
    op.execute(
        """
        UPDATE catalogs
        SET name = 'Canal de contacto'
        WHERE code = 'contact_channel'
        """
    )

    # Desactivar y quitar flag de sistema a la opción REFERENCIA (es un origen, no un canal)
    op.execute(
        """
        UPDATE catalog_options
        SET is_system = false, is_active = false
        WHERE code = 'REFERENCIA'
          AND catalog_id = (SELECT id FROM catalogs WHERE code = 'contact_channel')
        """
    )

    # Alinear nombres de opciones con la nueva semántica de canal de contacto inicial
    op.execute(
        """
        UPDATE catalog_options
        SET name = 'Formulario web'
        WHERE code = 'WEB'
          AND catalog_id = (SELECT id FROM catalogs WHERE code = 'contact_channel')
        """
    )
    op.execute(
        """
        UPDATE catalog_options
        SET name = 'Messenger / Facebook'
        WHERE code = 'FACEBOOK'
          AND catalog_id = (SELECT id FROM catalogs WHERE code = 'contact_channel')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE catalogs
        SET name = 'Forma de contacto'
        WHERE code = 'contact_channel'
        """
    )
    op.execute(
        """
        UPDATE catalog_options
        SET is_system = true, is_active = true
        WHERE code = 'REFERENCIA'
          AND catalog_id = (SELECT id FROM catalogs WHERE code = 'contact_channel')
        """
    )
    op.execute(
        """
        UPDATE catalog_options
        SET name = 'Web'
        WHERE code = 'WEB'
          AND catalog_id = (SELECT id FROM catalogs WHERE code = 'contact_channel')
        """
    )
    op.execute(
        """
        UPDATE catalog_options
        SET name = 'Facebook'
        WHERE code = 'FACEBOOK'
          AND catalog_id = (SELECT id FROM catalogs WHERE code = 'contact_channel')
        """
    )
