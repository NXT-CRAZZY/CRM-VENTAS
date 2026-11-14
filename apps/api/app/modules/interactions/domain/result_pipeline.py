"""Conexión entre el resultado de una interacción y el pipeline de oportunidades.

Resultado (catálogo `contact_result`) -> etapa (catálogo `pipeline_stage`).
Los resultados que no aparecen aquí (VOLVER_LLAMAR, SIN_RESPUESTA) no tocan el pipeline.
"""

RESULT_TO_STAGE: dict[str, str] = {
    "CONTESTO": "NUEVO",
    "DEMOSTRACION": "DEMOSTRACION",
    "COTIZACION": "COTIZACION",
    "VENTA": "CERRADO_GANADO",
    "NO_INTERESADO": "CERRADO_PERDIDO",
}

# Etapas abiertas, de menor a mayor avance: una oportunidad abierta solo avanza, nunca retrocede.
OPEN_STAGE_ORDER: list[str] = ["NUEVO", "DEMOSTRACION", "COTIZACION"]
CLOSED_STAGES: set[str] = {"CERRADO_GANADO", "CERRADO_PERDIDO"}

STAGE_PROBABILITY: dict[str, int] = {
    "NUEVO": 10,
    "DEMOSTRACION": 25,
    "COTIZACION": 50,
    "CERRADO_GANADO": 100,
    "CERRADO_PERDIDO": 0,
}
