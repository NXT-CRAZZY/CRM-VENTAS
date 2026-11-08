from enum import StrEnum


class ProductKind(StrEnum):
    LICENCIA_PERPETUA = "LICENCIA_PERPETUA"
    SUSCRIPCION = "SUSCRIPCION"
    USUARIO_ADICIONAL = "USUARIO_ADICIONAL"
    DEMO = "DEMO"


class BillingPeriod(StrEnum):
    """Determina la fecha de renovación de lo vendido (usado por las alertas de renovación)."""

    UNICO = "UNICO"
    SEMANAL = "SEMANAL"
    MENSUAL = "MENSUAL"
    ANUAL = "ANUAL"


PRODUCT_LINES = ("DS-CONT", "DS_BUSINESS", "DSCONT CLOUD")
