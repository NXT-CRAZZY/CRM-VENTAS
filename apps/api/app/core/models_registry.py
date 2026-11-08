"""Importa todos los modelos para que Alembic y SQLAlchemy conozcan el esquema completo."""

from app.modules.alerts.infrastructure.models import Alert  # noqa: F401
from app.modules.audit.infrastructure.models import AuditLog  # noqa: F401
from app.modules.auth.infrastructure.models import RefreshToken  # noqa: F401
from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption  # noqa: F401
from app.modules.imports.infrastructure.models import ImportJob, ImportRowError  # noqa: F401
from app.modules.interactions.infrastructure.models import Interaction  # noqa: F401
from app.modules.opportunities.infrastructure.models import Opportunity  # noqa: F401
from app.modules.products.infrastructure.models import Product, ProductCategory  # noqa: F401
from app.modules.prospects.infrastructure.models import (  # noqa: F401
    Prospect,
    ProspectAssignment,
    ProspectContact,
    ProspectStatusHistory,
    ProspectTag,
    Tag,
)
from app.modules.quotes.infrastructure.models import Quote, QuoteItem  # noqa: F401
from app.modules.rbac.infrastructure.models import Permission, Role  # noqa: F401
from app.modules.settings.infrastructure.models import AppSetting  # noqa: F401
from app.modules.tasks.infrastructure.models import Task  # noqa: F401
from app.modules.users.infrastructure.models import User  # noqa: F401
