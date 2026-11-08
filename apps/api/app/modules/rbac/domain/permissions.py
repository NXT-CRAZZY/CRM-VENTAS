"""Registro de permisos del sistema.

Los *códigos* viven en código porque los endpoints los verifican; la asignación de
permisos a roles vive en la base de datos y se administra desde la interfaz.
Los permisos de módulos aún no construidos se registran desde ya para que la
matriz de roles quede completa y estable entre fases.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDef:
    code: str
    module: str
    name: str


class P:
    USERS_READ = "users.read"
    USERS_MANAGE = "users.manage"
    ROLES_READ = "roles.read"
    ROLES_MANAGE = "roles.manage"
    CATALOGS_MANAGE = "catalogs.manage"
    PRODUCTS_READ = "products.read"
    PRODUCTS_MANAGE = "products.manage"
    SETTINGS_READ = "settings.read"
    SETTINGS_MANAGE = "settings.manage"
    AUDIT_READ = "audit.read"

    PROSPECTS_READ_OWN = "prospects.read.own"
    PROSPECTS_READ_ALL = "prospects.read.all"
    PROSPECTS_CREATE = "prospects.create"
    PROSPECTS_UPDATE_OWN = "prospects.update.own"
    PROSPECTS_UPDATE_ALL = "prospects.update.all"
    PROSPECTS_ASSIGN = "prospects.assign"
    PROSPECTS_DELETE = "prospects.delete"
    PROSPECTS_CONVERT = "prospects.convert"
    INTERACTIONS_CREATE = "interactions.create"
    TASKS_MANAGE = "tasks.manage"
    OPPORTUNITIES_MANAGE = "opportunities.manage"
    QUOTES_MANAGE = "quotes.manage"
    SALES_MANAGE = "sales.manage"
    DASHBOARD_SALES = "dashboard.sales"
    DASHBOARD_MANAGEMENT = "dashboard.management"
    REPORTS_EXPORT = "reports.export"
    IMPORT_RUN = "import.run"


PERMISSIONS: list[PermissionDef] = [
    PermissionDef(P.USERS_READ, "Usuarios", "Ver usuarios"),
    PermissionDef(P.USERS_MANAGE, "Usuarios", "Crear, editar y desactivar usuarios"),
    PermissionDef(P.ROLES_READ, "Roles y permisos", "Ver roles y permisos"),
    PermissionDef(P.ROLES_MANAGE, "Roles y permisos", "Gestionar roles y permisos"),
    PermissionDef(P.CATALOGS_MANAGE, "Catálogos", "Gestionar catálogos"),
    PermissionDef(P.PRODUCTS_READ, "Productos", "Ver productos"),
    PermissionDef(P.PRODUCTS_MANAGE, "Productos", "Gestionar productos y categorías"),
    PermissionDef(P.SETTINGS_READ, "Configuración", "Ver configuración"),
    PermissionDef(P.SETTINGS_MANAGE, "Configuración", "Modificar configuración"),
    PermissionDef(P.AUDIT_READ, "Auditoría", "Consultar auditoría"),
    PermissionDef(P.PROSPECTS_READ_OWN, "Prospectos", "Ver sus prospectos asignados"),
    PermissionDef(P.PROSPECTS_READ_ALL, "Prospectos", "Ver todos los prospectos"),
    PermissionDef(P.PROSPECTS_CREATE, "Prospectos", "Crear prospectos"),
    PermissionDef(P.PROSPECTS_UPDATE_OWN, "Prospectos", "Editar sus prospectos"),
    PermissionDef(P.PROSPECTS_UPDATE_ALL, "Prospectos", "Editar cualquier prospecto"),
    PermissionDef(P.PROSPECTS_ASSIGN, "Prospectos", "Asignar y reasignar prospectos"),
    PermissionDef(P.PROSPECTS_DELETE, "Prospectos", "Eliminar (papelera) prospectos"),
    PermissionDef(P.PROSPECTS_CONVERT, "Prospectos", "Convertir prospectos en clientes"),
    PermissionDef(P.INTERACTIONS_CREATE, "Seguimiento", "Registrar interacciones"),
    PermissionDef(P.TASKS_MANAGE, "Seguimiento", "Gestionar tareas y recordatorios"),
    PermissionDef(P.OPPORTUNITIES_MANAGE, "Pipeline", "Gestionar oportunidades"),
    PermissionDef(P.QUOTES_MANAGE, "Cotizaciones", "Gestionar cotizaciones"),
    PermissionDef(P.SALES_MANAGE, "Ventas", "Registrar y editar ventas"),
    PermissionDef(P.DASHBOARD_SALES, "Dashboards", "Dashboard de ventas"),
    PermissionDef(P.DASHBOARD_MANAGEMENT, "Dashboards", "Dashboard gerencial"),
    PermissionDef(P.REPORTS_EXPORT, "Reportes", "Exportar reportes"),
    PermissionDef(P.IMPORT_RUN, "Reportes", "Importar Excel legacy"),
]

ALL_CODES = [p.code for p in PERMISSIONS]

SALES_CODES = [
    P.PRODUCTS_READ,
    P.PROSPECTS_READ_OWN,
    P.PROSPECTS_CREATE,
    P.PROSPECTS_UPDATE_OWN,
    P.PROSPECTS_CONVERT,
    P.INTERACTIONS_CREATE,
    P.TASKS_MANAGE,
    P.OPPORTUNITIES_MANAGE,
    P.QUOTES_MANAGE,
    P.SALES_MANAGE,
    P.DASHBOARD_SALES,
]

MANAGER_CODES = [
    c for c in ALL_CODES if c not in (P.ROLES_MANAGE, P.SETTINGS_MANAGE, P.PROSPECTS_READ_OWN, P.PROSPECTS_UPDATE_OWN)
]

# Roles base: (code, nombre, descripción, permisos)
SYSTEM_ROLES = [
    ("ADMIN", "Administrador", "Acceso total, incluida la configuración del sistema", ALL_CODES),
    ("MANAGER", "Gerente", "Ve y gestiona toda la operación comercial", MANAGER_CODES),
    ("SALES", "Ventas", "Gestiona sus prospectos, seguimientos, cotizaciones y ventas", SALES_CODES),
]
