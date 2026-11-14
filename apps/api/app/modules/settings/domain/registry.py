"""Definición tipada de cada grupo de configuración.

Cada clave guarda un objeto JSON validado por su modelo; así los valores son
configurables desde la interfaz pero siempre consistentes.
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class GeneralSettings(BaseModel):
    company_name: str = Field("DATA SERVICE", min_length=2, max_length=120, title="Nombre de la empresa")
    currency: str = Field("PEN", pattern=r"^[A-Z]{3}$", title="Moneda")
    timezone: str = Field("America/Lima", title="Zona horaria")


class ProspectSettings(BaseModel):
    document_unique: bool = Field(True, title="El documento (DNI/RUC) debe ser único")
    name_similarity_threshold: float = Field(
        0.6, ge=0.3, le=0.95, title="Similitud mínima para advertir posible duplicado por nombre"
    )


class AlertSettings(BaseModel):
    uncontacted_hours: int = Field(24, ge=1, le=720, title="Horas máximas sin primer contacto")
    no_followup_days: int = Field(7, ge=1, le=180, title="Días sin seguimiento para alertar")
    no_contact_days: int = Field(7, ge=1, le=180, title="Días sin contacto para considerar prospecto desatendido")
    quote_expiring_days: int = Field(3, ge=1, le=60, title="Días de aviso antes del vencimiento de cotización")
    quote_no_response_days: int = Field(5, ge=1, le=90, title="Días de cotización enviada sin respuesta")
    quote_validity_days: int = Field(15, ge=1, le=365, title="Días de vigencia por defecto de una cotización")
    high_value_amount: Decimal = Field(Decimal("5000"), ge=0, title="Monto (S/) considerado de alto valor")
    max_attempts: int = Field(6, ge=1, le=50, title="Intentos de contacto que disparan alerta")
    renewal_notice_days: list[int] = Field(
        default_factory=lambda: [30, 15, 7], title="Días de aviso antes de una renovación"
    )


SETTINGS_REGISTRY: dict[str, tuple[str, type[BaseModel]]] = {
    "general": ("General", GeneralSettings),
    "prospects": ("Prospectos", ProspectSettings),
    "alerts": ("Alertas y seguimiento", AlertSettings),
}
