"""Catálogos iniciales. Incluyen los códigos del Excel FOR-VEN-001 como `legacy_code`.

Formato de cada opción: (code, nombre, legacy_code, color, peso, es_sistema)
Las opciones marcadas como sistema pueden renombrarse/recolorearse, pero no desactivarse
ni cambiar de código, porque reglas del CRM dependen de ellas.
"""

# Paleta de estados (independiente del naranja de marca)
GREEN, AMBER, RED, BLUE, GRAY, VIOLET, TEAL = (
    "#16A34A",
    "#D97706",
    "#DC2626",
    "#2563EB",
    "#71717A",
    "#7C3AED",
    "#0D9488",
)

# (code, nombre, descripción, usa_color, usa_peso, opciones)
CATALOGS = [
    (
        "document_type",
        "Tipo de documento",
        "Documento de identidad del prospecto",
        False,
        False,
        [
            ("DNI", "DNI", None, None, None, True),
            ("RUC", "RUC", None, None, None, True),
            ("CE", "Carné de extranjería", None, None, None, False),
            ("PASAPORTE", "Pasaporte", None, None, None, False),
        ],
    ),
    (
        "contact_channel",
        "Forma de contacto",
        "Medio por el que se realizó el contacto",
        True,
        False,
        [
            ("CORREO", "Correo", "C", BLUE, None, True),
            ("TELEFONO", "Teléfono", "T", GREEN, None, True),
            ("VISITA", "Visita", "V", VIOLET, None, True),
            ("WEB", "Web", "W", TEAL, None, True),
            ("FACEBOOK", "Facebook", "F", "#1877F2", None, True),
            ("REFERENCIA", "Referencia de otro cliente", "R", AMBER, None, True),
            ("WHATSAPP", "WhatsApp", None, "#25D366", None, False),
        ],
    ),
    (
        "contact_mode",
        "Modalidad de contacto",
        "Si el contacto fue presencial o remoto",
        False,
        False,
        [
            ("PRESENCIAL", "Presencial", "P", None, None, True),
            ("REMOTO", "Remoto", "R", None, None, True),
        ],
    ),
    (
        "contact_result",
        "Resultado del contacto",
        "Logro obtenido en la interacción",
        True,
        False,
        [
            ("COTIZACION", "Cotización", "C", BLUE, None, True),
            ("DEMOSTRACION", "Demostración", "D", VIOLET, None, True),
            ("VENTA", "Venta", "V", GREEN, None, True),
            ("CONTESTO", "Contestó / interesado", None, TEAL, None, False),
            ("VOLVER_LLAMAR", "Volver a llamar", None, AMBER, None, False),
            ("SIN_RESPUESTA", "Sin respuesta", None, GRAY, None, False),
            ("NO_INTERESADO", "No interesado", None, RED, None, False),
        ],
    ),
    (
        "interest_level",
        "Nivel de interés",
        "Interés detectado en el prospecto",
        True,
        True,
        [
            ("ALTO", "Alto", None, GREEN, 30, True),
            ("REGULAR", "Regular", None, AMBER, 15, True),
            ("BAJO", "Bajo", None, GRAY, 5, True),
        ],
    ),
    (
        "opportunity_type",
        "Tipo comercial",
        "Distingue ventas de actualización y de clientes nuevos",
        True,
        False,
        [
            ("ACTUALIZACION", "Actualización", "A", BLUE, None, True),
            ("NUEVO", "Nuevo cliente", "N", GREEN, None, True),
        ],
    ),
    (
        "prospect_source",
        "Origen del prospecto",
        "Cómo llegó el prospecto a DATA SERVICE",
        False,
        False,
        [
            ("WEB", "Página web", None, None, None, False),
            ("FACEBOOK", "Facebook", None, None, None, False),
            ("REFERIDO", "Referido por cliente", None, None, None, False),
            ("LLAMADA_ENTRANTE", "Llamada entrante", None, None, None, False),
            ("VISITA", "Visita comercial", None, None, None, False),
            ("FERIA", "Feria / evento", None, None, None, False),
            ("BASE_DATOS", "Base de datos propia", None, None, None, False),
            ("OTRO", "Otro", None, None, None, False),
        ],
    ),
    (
        "priority",
        "Prioridad",
        "Prioridad de prospectos y tareas",
        True,
        True,
        [
            ("ALTA", "Alta", None, RED, 3, True),
            ("MEDIA", "Media", None, AMBER, 2, True),
            ("BAJA", "Baja", None, GRAY, 1, True),
        ],
    ),
    (
        "loss_reason",
        "Motivo de pérdida",
        "Por qué se perdió una oportunidad",
        False,
        False,
        [
            ("PRECIO", "Precio", None, None, None, False),
            ("NO_RESPONDIO", "No respondió", None, None, None, False),
            ("COMPETENCIA", "Eligió a la competencia", None, None, None, False),
            ("SIN_PRESUPUESTO", "No tiene presupuesto", None, None, None, False),
            ("POSTERGADO", "Proyecto postergado", None, None, None, False),
            ("NO_NECESITA", "No necesita el producto", None, None, None, False),
            ("INFO_INCORRECTA", "Información incorrecta", None, None, None, False),
            ("OTRO", "Otro", None, None, None, True),
        ],
    ),
    (
        "discard_reason",
        "Motivo de descarte",
        "Por qué se deja de trabajar un prospecto",
        False,
        False,
        [
            ("NO_CALIFICA", "No califica", None, None, None, False),
            ("DATOS_ERRONEOS", "Datos erróneos / inubicable", None, None, None, False),
            ("PIDIO_NO_CONTACTAR", "Pidió no ser contactado", None, None, None, False),
            ("DUPLICADO", "Registro duplicado", None, None, None, False),
            ("OTRO", "Otro", None, None, None, True),
        ],
    ),
    (
        "task_type",
        "Tipo de tarea",
        "Acciones de seguimiento programables",
        True,
        False,
        [
            ("LLAMAR", "Llamar", None, GREEN, None, True),
            ("CORREO", "Enviar correo", None, BLUE, None, True),
            ("COTIZACION", "Enviar cotización", None, VIOLET, None, False),
            ("VISITA", "Realizar visita", None, AMBER, None, False),
            ("DEMO", "Realizar demostración", None, TEAL, None, False),
            ("CONSULTAR_DECISION", "Consultar decisión", None, GRAY, None, False),
            ("RENOVACION", "Gestionar renovación", None, BLUE, None, True),
        ],
    ),
    (
        "pipeline_stage",
        "Etapa del pipeline",
        "Etapas por las que pasa una oportunidad de venta",
        True,
        True,
        [
            ("NUEVO", "Nuevo", None, GRAY, 10, True),
            ("COTIZACION", "Cotización", None, BLUE, 20, True),
            ("NEGOCIACION", "Negociación", None, AMBER, 30, True),
            ("CERRADO_GANADO", "Cerrado ganado", None, GREEN, 40, True),
            ("CERRADO_PERDIDO", "Cerrado perdido", None, RED, 50, True),
        ],
    ),
]
