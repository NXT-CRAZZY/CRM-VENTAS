"""Datos de demostración completos para el usuario Gianfranco.

Crea prospectos (personas naturales y jurídicas, clientes y prospectos, todos los
estados y orígenes), contactos, etiquetas, historial de estados, reasignaciones,
interacciones (todos los canales y resultados), tareas (todos los tipos y estados),
oportunidades en todas las etapas, cotizaciones en todos los estados, alertas de
todos los tipos/severidades, registros de auditoría y un rol de prueba para que
Gianfranco pueda ver todas las pantallas sin perder el alcance de "sus prospectos".

Uso (desde apps/api):
    .venv\\Scripts\\python.exe scripts\\seed_demo_gianfranco.py
    .venv\\Scripts\\python.exe scripts\\seed_demo_gianfranco.py --reset

El script es seguro de ejecutar varias veces: sin --reset se niega a duplicar los
datos si el usuario ya tiene prospectos.
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select

import app.core.models_registry  # noqa: F401
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.modules.alerts.application.use_cases import AlertService
from app.modules.alerts.infrastructure.models import Alert
from app.modules.audit.infrastructure.models import AuditLog
from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.interactions.infrastructure.models import Interaction
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.products.infrastructure.models import Product
from app.modules.prospects.infrastructure.models import (
    Prospect,
    ProspectAssignment,
    ProspectContact,
    ProspectStatusHistory,
    Tag,
)
from app.modules.quotes.infrastructure.models import Quote, QuoteItem
from app.modules.rbac.domain.permissions import P, SALES_CODES
from app.modules.rbac.infrastructure.models import Permission, Role
from app.modules.scoring.application.use_cases import ScoreCalculator
from app.modules.tasks.infrastructure.models import Task
from app.modules.users.infrastructure.models import User

NOW = datetime.now(UTC)
ADMIN_ID = 1
TARGET_EMAIL = "gfcharalla@dataservice.pe"
DEMO_PASSWORD = "Demo1234"


def dt(days: int = 0, hours: int = 0, minutes: int = 0) -> datetime:
    return NOW + timedelta(days=days, hours=hours, minutes=minutes)


def d(days: int = 0) -> date:
    return date.today() + timedelta(days=days)


# ─────────────────────────────────────────────────────────────────────────────
# Prospectos
# ─────────────────────────────────────────────────────────────────────────────
PROSPECTS: list[dict] = [
    {
        "key": "p1", "person_type": "NATURAL", "first_name": "Jorge Luis", "last_name": "Mendoza Quispe",
        "document": "DNI", "document_number": "70123456", "birth_date": date(1985, 4, 12),
        "email": "jorge.mendoza@gmail.com", "phone": "987654321", "whatsapp": "987654321",
        "address": "Av. Los Álamos 245, Surco, Lima",
        "source": "OTRO", "channel": "WHATSAPP", "interest": "ALTO", "priority": "ALTA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(hours=-6),
        "tags": ["VIP", "Alto potencial"],
        "notes": "Gerente de administración. Solicitó demo del módulo de ventas y facturación electrónica.",
    },
    {
        "key": "p2", "person_type": "JURIDICA", "legal_name": "Distribuidora Andina del Pacífico S.A.C.",
        "trade_name": "Andina Pacífico", "document": "RUC", "document_number": "20555100001",
        "email": "compras@andinapacifico.pe", "phone": "014567890", "whatsapp": "987111222",
        "address": "Av. Argentina 1520, Callao",
        "source": "REFERIDO", "channel": "VISITA", "interest": "REGULAR", "priority": "MEDIA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(days=-9),
        "tags": ["Referido"],
        "notes": "Referida por Ferretería El Constructor. Evalúan 2 terminales y usuarios adicionales.",
        "contacts": [
            {"full_name": "Patricia Salinas Ríos", "position": "Gerente General", "area": "Dirección",
             "email": "psalinas@andinapacifico.pe", "phone": "987111222", "whatsapp": "987111222",
             "is_primary": True, "notes": "Contacto principal. Prefiere reuniones por la mañana."},
            {"full_name": "Carlos Vega Núñez", "position": "Jefe de Logística", "area": "Operaciones",
             "email": "cvega@andinapacifico.pe", "phone": "987333444", "is_primary": False},
        ],
    },
    {
        "key": "p3", "person_type": "JURIDICA", "legal_name": "Ferretería El Constructor E.I.R.L.",
        "trade_name": "El Constructor", "document": "RUC", "document_number": "20555100002",
        "email": "administracion@elconstructor.pe", "phone": "014444555", "whatsapp": "987555666",
        "address": "Jr. Puno 455, Cercado de Lima",
        "source": "BASE_DATOS", "channel": "TELEFONO", "interest": "ALTO", "priority": "ALTA",
        "status": "ACTIVO", "relationship": "CLIENTE", "created": dt(days=-150),
        "converted_at": dt(days=-2), "tags": ["VIP", "Renovación próxima"],
        "notes": "Cliente desde hace 3 años. Renovación anual aceptada; generar factura y credenciales.",
    },
    {
        "key": "p4", "person_type": "NATURAL", "first_name": "Rosa Elena", "last_name": "Ticona Mamani",
        "document": "DNI", "document_number": "70234567", "birth_date": date(1990, 8, 3),
        "email": "rosa.ticona@gmail.com", "phone": "986222333", "whatsapp": "986222333",
        "address": "Calle Los Cedros 118, San Miguel, Lima",
        "source": "FACEBOOK", "channel": "FACEBOOK", "interest": "REGULAR", "priority": "BAJA",
        "status": "EN_PAUSA", "relationship": "PROSPECTO", "created": dt(days=-40),
        "status_changed": dt(days=-12), "status_reason": "Cliente pidió retomar el contacto en un mes.",
        "tags": ["Frío"],
        "notes": "Contacto por Facebook; no responde. Se pausa hasta nuevo aviso.",
    },
    {
        "key": "p5", "person_type": "NATURAL", "first_name": "Pedro Pablo", "last_name": "Cárdenas Ríos",
        "document": "DNI", "document_number": "70345678", "birth_date": date(1978, 1, 25),
        "email": "pedro.cardenas@outlook.com", "phone": "985333444",
        "address": "Av. Grau 980, Barranco, Lima",
        "source": "OTRO", "channel": "TELEFONO", "interest": "BAJO", "priority": "BAJA",
        "status": "DESCARTADO", "relationship": "PROSPECTO", "created": dt(days=-25),
        "status_changed": dt(days=-21), "status_reason": "Solicitó expresamente no ser contactado.",
        "discard_reason": "PIDIO_NO_CONTACTAR", "tags": ["Frío"],
        "notes": "Llamó para pedir que no lo contacten más. Respetar solicitud.",
    },
    {
        "key": "p6", "person_type": "JURIDICA", "legal_name": "Restaurante Sabor Criollo S.A.C.",
        "trade_name": "Sabor Criollo", "document": "RUC", "document_number": "20555100003",
        "email": "gerencia@saborcriollo.pe", "phone": "014777888", "whatsapp": "987777888",
        "address": "Av. Larco 345, Miraflores, Lima",
        "source": "FERIA", "channel": "VISITA", "interest": "BAJO", "priority": "BAJA",
        "status": "NO_CALIFICA", "relationship": "PROSPECTO", "created": dt(days=-18),
        "status_changed": dt(days=-17), "status_reason": "Ya cuenta con un sistema implementado y no desea cambiar.",
        "discard_reason": "NO_CALIFICA", "notes": "Contacto en feria gastronómica. Usa otro proveedor.",
        "contacts": [
            {"full_name": "Chef Marco Aurelio Díaz", "position": "Propietario", "area": "Gerencia",
             "phone": "987777888", "is_primary": True},
        ],
    },
    {
        "key": "p7", "person_type": "NATURAL", "first_name": "Marisol", "last_name": "Huamán Flores",
        "document": "DNI", "document_number": "70456789", "birth_date": date(1982, 11, 9),
        "email": "marisol.huaman@gmail.com", "phone": "984444555", "whatsapp": "984444555",
        "address": "Av. Aviación 2100, San Borja, Lima",
        "source": "OTRO", "channel": "VISITA", "interest": "REGULAR", "priority": "MEDIA",
        "status": "INACTIVO", "relationship": "PROSPECTO", "created": dt(days=-90),
        "status_changed": dt(days=-20), "status_reason": "Sin respuesta tras varios intentos; pasa a inactivo.",
        "tags": ["Recuperar"],
        "notes": "Interesada pero sin presupuesto. Retomar el próximo trimestre.",
    },
    {
        "key": "p8", "person_type": "JURIDICA", "legal_name": "Constructora Vértice Perú S.A.C.",
        "trade_name": "Vértice Perú", "document": "RUC", "document_number": "20555100004",
        "email": "proyectos@verticeperu.pe", "phone": "016666777", "whatsapp": "986666777",
        "address": "Av. Javier Prado Este 4200, Surco, Lima",
        "source": "OTRO", "channel": "CORREO", "interest": "ALTO", "priority": "ALTA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(days=-60),
        "tags": ["Recuperar", "Alto potencial"],
        "notes": "Cotización enviada hace 10 días sin respuesta. Muchos intentos de contacto.",
        "contacts": [
            {"full_name": "Ing. Raúl Paredes Soto", "position": "Gerente de Proyectos", "area": "Proyectos",
             "email": "rperedes@verticeperu.pe", "phone": "986666777", "whatsapp": "986666777",
             "is_primary": True},
            {"full_name": "Lucía Campos Vera", "position": "Asistente de Compras", "area": "Logística",
             "email": "lcampos@verticeperu.pe", "phone": "986666778", "is_primary": False},
        ],
    },
    {
        "key": "p9", "person_type": "NATURAL", "first_name": "Luis Alberto", "last_name": "Chávez Rojas",
        "document": "DNI", "document_number": "70567890", "birth_date": date(1993, 6, 30),
        "email": "luis.chavez@gmail.com", "phone": "983555666",
        "address": "Jr. Amazonas 560, Jesús María, Lima",
        "source": "OTRO", "channel": None, "interest": None, "priority": "MEDIA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(hours=-30),
        "tags": ["Frío"],
        "notes": "Registrado desde la web pero aún no se le contacta.",
    },
    {
        "key": "p10", "person_type": "JURIDICA", "legal_name": "Clínica San Rafael S.A.C.",
        "trade_name": "Clínica San Rafael", "document": "RUC", "document_number": "20555100005",
        "email": "direccion@clinicasanrafael.pe", "phone": "017777888", "whatsapp": "985123456",
        "address": "Av. Guardia Civil 980, San Isidro, Lima",
        "source": "FERIA", "channel": "WHATSAPP", "interest": "ALTO", "priority": "ALTA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(days=-20),
        "tags": ["Alto potencial", "VIP"],
        "notes": "Tres sedes. Requieren facturación electrónica y control de inventarios.",
        "contacts": [
            {"full_name": "Dra. Verónica Paredes Luna", "position": "Directora Médica", "area": "Dirección",
             "email": "vparedes@clinicasanrafael.pe", "phone": "985123456", "whatsapp": "985123456",
             "is_primary": True},
            {"full_name": "Sr. Hugo Ramírez Paz", "position": "Administrador", "area": "Administración",
             "email": "hramirez@clinicasanrafael.pe", "phone": "985123457", "is_primary": False},
        ],
    },
    {
        "key": "p11", "person_type": "NATURAL", "first_name": "Ana Lucía", "last_name": "Paredes Vargas",
        "document": "DNI", "document_number": "70678901", "birth_date": date(1988, 2, 14),
        "email": "ana.paredes@gmail.com", "phone": "982444555", "whatsapp": "982444555",
        "address": "Calle Schell 310, Miraflores, Lima",
        "source": "BASE_DATOS", "channel": "TELEFONO", "interest": "ALTO", "priority": "ALTA",
        "status": "ACTIVO", "relationship": "CLIENTE", "created": dt(days=-240),
        "converted_at": dt(days=-40), "tags": ["VIP"],
        "notes": "Cliente recurrente. Renovó en octubre; evaluar upgrade en el próximo ciclo.",
    },
    {
        "key": "p12", "person_type": "NATURAL", "first_name": "Miguel Ángel", "last_name": "Torres Salazar",
        "document": "DNI", "document_number": "70789012", "birth_date": date(1975, 9, 8),
        "email": "miguel.torres@hotmail.com", "phone": "981333444", "whatsapp": "981333444",
        "address": "Av. Universitaria 1850, Los Olivos, Lima",
        "source": "REFERIDO", "channel": "WHATSAPP", "interest": "REGULAR", "priority": "MEDIA",
        "status": "ACTIVO", "relationship": "CLIENTE", "created": dt(days=-35),
        "converted_at": dt(hours=-3), "tags": ["Referido"],
        "notes": "Nuevo cliente. Implementación DS-BUSINESS Starter aceptada y pagada hoy.",
    },
    {
        "key": "p13", "person_type": "JURIDICA", "legal_name": "Textiles del Norte S.A.C.",
        "trade_name": "Textiles del Norte", "document": "RUC", "document_number": "20555100006",
        "email": "ventas@textilesnorte.pe", "phone": "044234567", "whatsapp": "944123456",
        "address": "Av. Larco 780, Trujillo, La Libertad",
        "source": "OTRO", "channel": "CORREO", "interest": "REGULAR", "priority": "ALTA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(days=-70),
        "notes": "Perdieron la oportunidad por precio; mantener seguimiento para el próximo año.",
        "contacts": [
            {"full_name": "Sra. Julia Benites Campos", "position": "Gerente Comercial", "area": "Comercial",
             "email": "jbenites@textilesnorte.pe", "phone": "944123456", "is_primary": True},
        ],
    },
    {
        "key": "p14", "person_type": "NATURAL", "first_name": "Carmen Rosa", "last_name": "Villalobos Díaz",
        "document": "DNI", "document_number": "70890123", "birth_date": date(1969, 12, 1),
        "email": "carmen.villalobos@gmail.com", "phone": "980222333",
        "address": "Av. Bolívar 120, Pueblo Libre, Lima",
        "source": "FACEBOOK", "channel": "WEB", "interest": "BAJO", "priority": "MEDIA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(days=-15),
        "notes": "Dejó de responder después de la propuesta. Reintentar contacto.",
    },
    {
        "key": "p15", "person_type": "JURIDICA", "legal_name": "Importaciones Global Trade S.A.C.",
        "trade_name": "Global Trade", "document": "RUC", "document_number": "20555100007",
        "email": "operaciones@globaltrade.pe", "phone": "017888999", "whatsapp": "977888999",
        "address": "Av. Elmer Faucett 2340, Callao",
        "source": "REFERIDO", "channel": "VISITA", "interest": "ALTO", "priority": "ALTA",
        "status": "EN_PAUSA", "relationship": "PROSPECTO", "created": dt(days=-45),
        "status_changed": dt(days=-5), "status_reason": "Cliente evaluando presupuesto del próximo trimestre.",
        "tags": ["Recuperar", "Alto potencial"],
        "notes": "Oportunidad grande en negociación. Pausado por presupuesto hasta enero.",
        "contacts": [
            {"full_name": "Sr. Andrés Wong Lau", "position": "Gerente de Operaciones", "area": "Operaciones",
             "email": "awong@globaltrade.pe", "phone": "977888999", "whatsapp": "977888999",
             "is_primary": True},
        ],
    },
    {
        "key": "p16", "person_type": "NATURAL", "first_name": "José Antonio", "last_name": "Ramírez Ccahuana",
        "document": "DNI", "document_number": "70901234", "birth_date": date(1991, 3, 19),
        "email": "jose.ramirez@gmail.com", "phone": "979111222", "whatsapp": "979111222",
        "address": "Av. Túpac Amaru 3400, Comas, Lima",
        "source": "OTRO", "channel": "WEB", "interest": "REGULAR", "priority": "MEDIA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(days=-12),
        "notes": "Pidió demo del módulo de inventarios. Interesado en el plan Team.",
    },
    {
        "key": "p17", "person_type": "JURIDICA", "legal_name": "Farmacia Vida Sana S.A.C.",
        "trade_name": "Vida Sana", "document": None, "document_number": None,
        "email": "contacto@vidasana.pe", "phone": "015555666", "whatsapp": "966777888",
        "address": "Av. Arequipa 2450, Lince, Lima",
        "source": "OTRO", "channel": "WHATSAPP", "interest": "ALTO", "priority": "MEDIA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(hours=-26),
        "notes": "Llegó por recomendación; falta registrar RUC y asignar reunión.",
        "contacts": [
            {"full_name": "Q.F. Paula Mendoza Rojas", "position": "Química Farmacéutica", "area": "Dirección Técnica",
             "phone": "966777888", "whatsapp": "966777888", "is_primary": True},
        ],
    },
    {
        "key": "p18", "person_type": "NATURAL", "first_name": "Silvia Roxana", "last_name": "Núñez Campos",
        "document": "CE", "document_number": "001234567", "birth_date": date(1987, 7, 7),
        "email": "silvia.nunez@gmail.com", "phone": "965666777", "whatsapp": "965666777",
        "address": "Calle Cantuarias 180, Miraflores, Lima",
        "source": "FERIA", "channel": "VISITA", "interest": "REGULAR", "priority": "BAJA",
        "status": "ACTIVO", "relationship": "PROSPECTO", "created": dt(days=-30),
        "notes": "Cotización vencida. Contactar para renovar interés.",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Interacciones: (prospecto, cuándo, canal, modalidad, resultado, interés, nota, próxima acción, contacto)
# ─────────────────────────────────────────────────────────────────────────────
INTERACTIONS: list[dict] = [
    # p1: seguimiento activo, cotización enviada hoy
    {"p": "p1", "at": dt(hours=-9), "channel": "WHATSAPP", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "ALTO", "notes": "Se comunicó por WhatsApp; solicita demo del módulo de ventas.",
     "next": dt(hours=3), "next_desc": "Confirmar horario de demo"},
    {"p": "p1", "at": dt(hours=-8), "channel": "TELEFONO", "mode": "REMOTO", "result": "DEMOSTRACION",
     "interest": "ALTO", "notes": "Demo en línea realizada; le interesa el plan Advance anual.",
     "next": dt(hours=3), "next_desc": "Enviar cotización del plan Advance"},
    {"p": "p1", "at": dt(hours=-7), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "ALTO", "notes": "Se envió cotización del plan Advance anual con 2 usuarios adicionales.",
     "next": dt(hours=3), "next_desc": "Llamar para confirmar recepción"},
    # p2: visita presencial y cotización
    {"p": "p2", "at": dt(days=-6), "channel": "VISITA", "mode": "PRESENCIAL", "result": "CONTESTO",
     "interest": "REGULAR", "notes": "Visita a planta; evalúan DS-CONT Empresarial 2 terminales.",
     "next": dt(days=2), "next_desc": "Enviar cotización con usuarios adicionales", "contact": 0},
    {"p": "p2", "at": dt(days=-5), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "REGULAR", "notes": "Enviada cotización con 2 terminales adicionales.",
     "next": dt(days=2), "next_desc": "Confirmar recepción de la cotización", "contact": 1},
    # p3: renovación de cliente
    {"p": "p3", "at": dt(days=-7), "channel": "TELEFONO", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "ALTO", "notes": "Renovación anual; conforme con el servicio.",
     "next": dt(days=20), "next_desc": "Enviar factura de renovación"},
    {"p": "p3", "at": dt(days=-6), "channel": "TELEFONO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "ALTO", "notes": "Cotización de renovación enviada.",
     "next": dt(days=20), "next_desc": "Confirmar pago"},
    {"p": "p3", "at": dt(days=-5), "channel": "WHATSAPP", "mode": "REMOTO", "result": "VOLVER_LLAMAR",
     "interest": "ALTO", "notes": "Pide llamar el lunes para confirmar el pago.",
     "next": dt(days=20), "next_desc": "Llamar para confirmar pago"},
    {"p": "p3", "at": dt(days=-2), "channel": "VISITA", "mode": "PRESENCIAL", "result": "VENTA",
     "interest": "ALTO", "notes": "Renovación aceptada y pagada.",
     "next": dt(days=20), "next_desc": "Enviar factura y credenciales"},
    {"p": "p3", "at": dt(days=-1), "channel": "CORREO", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "ALTO", "notes": "Se envió factura y credenciales de acceso.",
     "next": dt(days=20), "next_desc": "Confirmar recepción de credenciales"},
    # p4: en pausa
    {"p": "p4", "at": dt(days=-10), "channel": "FACEBOOK", "mode": "REMOTO", "result": "SIN_RESPUESTA",
     "interest": "BAJO", "notes": "Mensaje por Facebook sin respuesta.",
     "next": dt(days=5), "next_desc": "Reintentar por WhatsApp"},
    # p5: descartado
    {"p": "p5", "at": dt(days=-22), "channel": "TELEFONO", "mode": "REMOTO", "result": "NO_INTERESADO",
     "interest": "BAJO", "notes": "Indicó que no desea ser contactado.", "next": None},
    {"p": "p5", "at": dt(days=-21), "channel": "TELEFONO", "mode": "REMOTO", "result": "NO_INTERESADO",
     "interest": "BAJO", "notes": "Confirmó que no desea recibir llamadas.", "next": None},
    # p6: no califica
    {"p": "p6", "at": dt(days=-17), "channel": "VISITA", "mode": "PRESENCIAL", "result": "NO_INTERESADO",
     "interest": "BAJO", "notes": "En feria indicó que ya usa otro sistema.", "next": None},
    # p7: inactivo, sin seguimiento
    {"p": "p7", "at": dt(days=-60), "channel": "VISITA", "mode": "PRESENCIAL", "result": "CONTESTO",
     "interest": "REGULAR", "notes": "Primera visita; interesada pero sin presupuesto.",
     "next": dt(days=5), "next_desc": "Llamar en quincena"},
    {"p": "p7", "at": dt(days=-50), "channel": "TELEFONO", "mode": "REMOTO", "result": "VOLVER_LLAMAR",
     "interest": "REGULAR", "notes": "Pidió llamar en quincena.", "next": dt(days=2), "next_desc": "Llamar según lo acordado"},
    {"p": "p7", "at": dt(days=-45), "channel": "TELEFONO", "mode": "REMOTO", "result": "SIN_RESPUESTA",
     "interest": "REGULAR", "notes": "No contestó; se dejó mensaje.", "next": dt(days=2), "next_desc": "Reintentar llamada"},
    # p8: estancado, 7 intentos, cotización sin respuesta
    {"p": "p8", "at": dt(days=-30), "channel": "CORREO", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "ALTO", "notes": "Se presentó propuesta inicial.", "next": dt(days=1), "next_desc": "Enviar detalle técnico", "contact": 0},
    {"p": "p8", "at": dt(days=-25), "channel": "CORREO", "mode": "REMOTO", "result": "SIN_RESPUESTA",
     "interest": "ALTO", "notes": "Sin respuesta al correo con la propuesta.", "next": dt(days=1), "next_desc": "Llamar a Raúl Paredes", "contact": 0},
    {"p": "p8", "at": dt(days=-20), "channel": "TELEFONO", "mode": "REMOTO", "result": "VOLVER_LLAMAR",
     "interest": "ALTO", "notes": "Pidió llamar al día siguiente.", "next": dt(days=1), "next_desc": "Llamar según lo acordado", "contact": 0},
    {"p": "p8", "at": dt(days=-18), "channel": "TELEFONO", "mode": "REMOTO", "result": "SIN_RESPUESTA",
     "interest": "ALTO", "notes": "No contestó.", "next": dt(days=1), "next_desc": "Enviar WhatsApp", "contact": 0},
    {"p": "p8", "at": dt(days=-15), "channel": "WHATSAPP", "mode": "REMOTO", "result": "SIN_RESPUESTA",
     "interest": "ALTO", "notes": "Mensaje de WhatsApp sin respuesta.", "next": dt(days=1), "next_desc": "Reintentar contacto", "contact": 1},
    {"p": "p8", "at": dt(days=-12), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "ALTO", "notes": "Cotización enviada con 2 terminales.", "next": dt(days=1), "next_desc": "Consultar decisión", "contact": 0},
    {"p": "p8", "at": dt(days=-8), "channel": "CORREO", "mode": "REMOTO", "result": "SIN_RESPUESTA",
     "interest": "ALTO", "notes": "Sin respuesta después de la cotización.", "next": dt(days=1), "next_desc": "Último intento de contacto", "contact": 0},
    # p10: cotización de 3 sedes
    {"p": "p10", "at": dt(days=-2), "channel": "WHATSAPP", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "ALTO", "notes": "Solicita propuesta para 3 sedes.", "next": dt(days=1), "next_desc": "Enviar propuesta", "contact": 0},
    {"p": "p10", "at": dt(hours=-6), "channel": "TELEFONO", "mode": "REMOTO", "result": "DEMOSTRACION",
     "interest": "ALTO", "notes": "Demostración del módulo contable realizada.", "next": dt(days=1), "next_desc": "Enviar cotización", "contact": 0},
    {"p": "p10", "at": dt(hours=-2), "channel": "WHATSAPP", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "ALTO", "notes": "Cotización enviada para 3 sedes.", "next": dt(days=3), "next_desc": "Confirmar recepción", "contact": 0},
    # p11: cliente del mes pasado
    {"p": "p11", "at": dt(days=-45), "channel": "TELEFONO", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "ALTO", "notes": "Renovación anual. Conforme con el servicio.", "next": dt(days=30), "next_desc": "Preparar renovación"},
    {"p": "p11", "at": dt(days=-42), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "ALTO", "notes": "Cotización de renovación enviada.", "next": dt(days=30), "next_desc": "Confirmar pago"},
    {"p": "p11", "at": dt(days=-40), "channel": "VISITA", "mode": "PRESENCIAL", "result": "VENTA",
     "interest": "ALTO", "notes": "Renovación aceptada y pagada.", "next": dt(days=30), "next_desc": "Enviar factura"},
    # p12: cliente nuevo de hoy
    {"p": "p12", "at": dt(days=-10), "channel": "WHATSAPP", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "REGULAR", "notes": "Interesado en DS-BUSINESS Starter.", "next": dt(days=1), "next_desc": "Enviar cotización"},
    {"p": "p12", "at": dt(days=-9), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "REGULAR", "notes": "Cotización enviada.", "next": dt(days=1), "next_desc": "Confirmar decisión"},
    {"p": "p12", "at": dt(days=-2), "channel": "TELEFONO", "mode": "REMOTO", "result": "VOLVER_LLAMAR",
     "interest": "REGULAR", "notes": "Pide llamar para coordinar pago.", "next": dt(days=1), "next_desc": "Confirmar pago"},
    {"p": "p12", "at": dt(hours=-4), "channel": "VISITA", "mode": "PRESENCIAL", "result": "VENTA",
     "interest": "REGULAR", "notes": "Venta cerrada; pago recibido.", "next": dt(days=30), "next_desc": "Coordinar implementación"},
    # p13: oportunidad perdida por precio
    {"p": "p13", "at": dt(days=-20), "channel": "TELEFONO", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "REGULAR", "notes": "Interesados en DS-CONT Empresarial.", "next": dt(days=3), "next_desc": "Enviar propuesta", "contact": 0},
    {"p": "p13", "at": dt(days=-15), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "REGULAR", "notes": "Cotización enviada.", "next": dt(days=3), "next_desc": "Consultar decisión", "contact": 0},
    {"p": "p13", "at": dt(days=-8), "channel": "TELEFONO", "mode": "REMOTO", "result": "NO_INTERESADO",
     "interest": "REGULAR", "notes": "Eligieron a la competencia por precio.", "next": dt(days=60), "next_desc": "Retomar en el próximo año", "contact": 0},
    # p14: sin respuesta, tarea vencida
    {"p": "p14", "at": dt(days=-14), "channel": "WEB", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "BAJO", "notes": "Completó formulario web.", "next": dt(days=1), "next_desc": "Enviar propuesta"},
    {"p": "p14", "at": dt(days=-12), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "BAJO", "notes": "Propuesta enviada; no responde.", "next": dt(days=-1), "next_desc": "Recontactar"},
    # p15: negociación grande, pausada
    {"p": "p15", "at": dt(days=-20), "channel": "VISITA", "mode": "PRESENCIAL", "result": "CONTESTO",
     "interest": "ALTO", "notes": "Reunión en Callao; interesados en upgrade.", "next": dt(days=1), "next_desc": "Enviar propuesta", "contact": 0},
    {"p": "p15", "at": dt(days=-15), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "ALTO", "notes": "Cotización de upgrade enviada.", "next": dt(days=1), "next_desc": "Consultar decisión", "contact": 0},
    {"p": "p15", "at": dt(days=-12), "channel": "WHATSAPP", "mode": "REMOTO", "result": "VOLVER_LLAMAR",
     "interest": "ALTO", "notes": "Piden retomar en enero por presupuesto.", "next": dt(days=30), "next_desc": "Retomar en enero", "contact": 0},
    # p16: demo de inventarios
    {"p": "p16", "at": dt(days=-11), "channel": "WEB", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "REGULAR", "notes": "Solicitó demo del módulo de inventarios.", "next": dt(hours=2), "next_desc": "Demo de inventarios"},
    {"p": "p16", "at": dt(days=-8), "channel": "TELEFONO", "mode": "REMOTO", "result": "CONTESTO",
     "interest": "REGULAR", "notes": "Confirmó interés en el plan Team.", "next": dt(hours=2), "next_desc": "Demo de inventarios"},
    {"p": "p16", "at": dt(days=-4), "channel": "WHATSAPP", "mode": "REMOTO", "result": "VOLVER_LLAMAR",
     "interest": "REGULAR", "notes": "Pide coordinar demo para esta semana.", "next": dt(hours=2), "next_desc": "Demo de inventarios"},
    {"p": "p16", "at": dt(days=-1), "channel": "CORREO", "mode": "REMOTO", "result": "COTIZACION",
     "interest": "REGULAR", "notes": "Envió requerimientos para la demo.", "next": dt(hours=2), "next_desc": "Demo de inventarios"},
    # p18: cotización vencida
    {"p": "p18", "at": dt(days=-27), "channel": "VISITA", "mode": "PRESENCIAL", "result": "CONTESTO",
     "interest": "REGULAR", "notes": "Contacto en feria; se envió información.", "next": dt(days=2), "next_desc": "Llamar para retomar"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Tareas
# ─────────────────────────────────────────────────────────────────────────────
TASKS: list[dict] = [
    {"p": "p1", "type": "LLAMAR", "priority": "ALTA", "title": "Llamar para confirmar demo",
     "description": "Confirmar horario de demo con el área contable.", "due": dt(hours=2), "status": "PENDING"},
    {"p": "p1", "type": "COTIZACION", "priority": "ALTA", "title": "Enviar cotización actualizada",
     "description": "Incluir 2 usuarios adicionales en la cotización del plan Advance.", "due": dt(days=1), "status": "PENDING"},
    {"p": "p2", "type": "VISITA", "priority": "MEDIA", "title": "Visitar planta de Andina Pacífico",
     "description": "Reunión presencial con Patricia Salinas y Carlos Vega.", "due": dt(days=2), "status": "PENDING"},
    {"p": "p3", "type": "RENOVACION", "priority": "ALTA", "title": "Gestionar renovación anual",
     "description": "Confirmar pago y emitir factura de renovación.", "due": dt(days=20), "status": "PENDING"},
    {"p": "p3", "type": "CORREO", "priority": "MEDIA", "title": "Enviar factura y credenciales",
     "description": "Enviar comprobante y accesos al cliente.", "due": dt(days=-1), "status": "DONE", "completed": dt(hours=-20)},
    {"p": "p4", "type": "CORREO", "priority": "BAJA", "title": "Reintentar contacto por correo",
     "description": "Enviar correo de seguimiento a Rosa Elena.", "due": dt(days=4), "status": "PENDING"},
    {"p": "p5", "type": "LLAMAR", "priority": "BAJA", "title": "Confirmar solicitud de no contacto",
     "description": "Registrar solicitud y no volver a contactar.", "due": dt(days=-21), "status": "CANCELLED"},
    {"p": "p7", "type": "LLAMAR", "priority": "MEDIA", "title": "Retomar contacto con Marisol",
     "description": "Llamar para retomar la conversación del trimestre.", "due": dt(days=-2), "status": "PENDING"},
    {"p": "p8", "type": "DEMO", "priority": "ALTA", "title": "Preparar demo para Vértice Perú",
     "description": "Preparar demo con datos de prueba del sector construcción.", "due": dt(days=1), "status": "PENDING"},
    {"p": "p8", "type": "CONSULTAR_DECISION", "priority": "ALTA", "title": "Consultar decisión de compra",
     "description": "Llamar a Raúl Paredes para conocer la decisión.", "due": dt(days=3), "status": "PENDING"},
    {"p": "p10", "type": "VISITA", "priority": "ALTA", "title": "Visitar Clínica San Rafael (3 sedes)",
     "description": "Coordinar visita a las sedes de San Isidro, Surco y La Molina.", "due": dt(days=3), "status": "PENDING"},
    {"p": "p12", "type": "CORREO", "priority": "MEDIA", "title": "Enviar agradecimiento y factura",
     "description": "Enviar correo de bienvenida y factura de implementación.", "due": dt(days=-1), "status": "DONE", "completed": dt(hours=-2)},
    {"p": "p14", "type": "LLAMAR", "priority": "MEDIA", "title": "Recontactar a Carmen Rosa",
     "description": "Llamar para retomar la propuesta enviada.", "due": dt(days=-1), "status": "PENDING"},
    {"p": "p15", "type": "CONSULTAR_DECISION", "priority": "ALTA", "title": "Consultar decisión de Global Trade",
     "description": "Retomar contacto por el upgrade de DS_BUSINESS.", "due": dt(days=1), "status": "PENDING"},
    {"p": "p16", "type": "DEMO", "priority": "MEDIA", "title": "Demo módulo de inventarios",
     "description": "Realizar demo en línea del módulo de inventarios.", "due": dt(hours=2), "status": "PENDING"},
    {"p": "p18", "type": "RENOVACION", "priority": "MEDIA", "title": "Gestionar renovación vencida",
     "description": "Reactivar la cotización vencida de Silvia Núñez.", "due": dt(days=2), "status": "PENDING"},
    {"p": "p1", "type": "LLAMAR", "priority": "ALTA", "title": "Llamada de seguimiento",
     "description": "Seguimiento inicial del prospecto.", "due": dt(days=-3), "status": "DONE", "completed": dt(days=-3, hours=2)},
    {"p": "p2", "type": "CORREO", "priority": "MEDIA", "title": "Enviar brochure institucional",
     "description": "Enviar brochure y casos de éxito del sector distribución.", "due": dt(days=-8), "status": "DONE", "completed": dt(days=-8, hours=1)},
    {"p": "p7", "type": "VISITA", "priority": "BAJA", "title": "Visita cancelada por el cliente",
     "description": "El cliente canceló la visita; se reprogramará.", "due": dt(days=-40), "status": "CANCELLED"},
    {"p": "p13", "type": "LLAMAR", "priority": "MEDIA", "title": "Llamar a Textiles del Norte",
     "description": "Seguimiento luego de la cotización.", "due": dt(days=-5), "status": "DONE", "completed": dt(days=-5, hours=3)},
]

# ─────────────────────────────────────────────────────────────────────────────
# Oportunidades
# ─────────────────────────────────────────────────────────────────────────────
OPPS: list[dict] = [
    {"key": "o1", "p": "p1", "stage": "NEGOCIACION", "type": "NUEVO",
     "title": "DS-CONT Cloud Advance para Mendoza", "amount": 9500, "probability": 70,
     "expected": d(15), "created": dt(days=-8),
     "description": "Plan Advance anual para 3 usuarios con facturación electrónica."},
    {"key": "o2", "p": "p2", "stage": "COTIZACION", "type": "NUEVO",
     "title": "DS-CONT Empresarial 2 terminales + usuarios", "amount": 6800, "probability": 50,
     "expected": d(20), "created": dt(days=-5),
     "description": "2 terminales, 2 usuarios adicionales y capacitación."},
    {"key": "o3", "p": "p3", "stage": "CERRADO_GANADO", "type": "ACTUALIZACION",
     "title": "Renovación anual DS-CONT Cloud Plus", "amount": 1500, "probability": 100,
     "expected": d(-2), "actual": d(0), "created": dt(days=-30),
     "description": "Renovación del plan Plus anual."},
    {"key": "o4", "p": "p10", "stage": "NUEVO", "type": "NUEVO",
     "title": "DS-CONT Cloud Advance 3 sedes", "amount": 12000, "probability": 40,
     "expected": d(30), "created": dt(days=-3),
     "description": "Implementación en 3 sedes con módulo de inventarios."},
    {"key": "o5", "p": "p11", "stage": "CERRADO_GANADO", "type": "ACTUALIZACION",
     "title": "Renovación DS-CONT Personal", "amount": 370, "probability": 100,
     "expected": d(-45), "actual": d(-40), "created": dt(days=-60),
     "description": "Renovación anual de licencia personal."},
    {"key": "o6", "p": "p12", "stage": "CERRADO_GANADO", "type": "NUEVO",
     "title": "Implementación DS-BUSINESS Starter", "amount": 6800, "probability": 100,
     "expected": d(0), "actual": d(0), "created": dt(hours=-3),
     "description": "Implementación inicial con facturación electrónica."},
    {"key": "o7", "p": "p13", "stage": "CERRADO_PERDIDO", "type": "NUEVO",
     "title": "DS-CONT Empresarial para Textiles del Norte", "amount": 5100, "probability": 0,
     "expected": d(-8), "actual": d(-8), "loss": "PRECIO", "created": dt(days=-20),
     "description": "Perdida por precio frente a la competencia."},
    {"key": "o8", "p": "p14", "stage": "CERRADO_PERDIDO", "type": "NUEVO",
     "title": "DS-CONT Personal para Carmen Rosa", "amount": 1470, "probability": 0,
     "expected": d(-10), "actual": d(-10), "loss": "NO_RESPONDIO", "created": dt(days=-14),
     "description": "El cliente no respondió después de la propuesta."},
    {"key": "o9", "p": "p15", "stage": "NEGOCIACION", "type": "ACTUALIZACION",
     "title": "Upgrade a DS_BUSINESS Emprendedor", "amount": 18000, "probability": 60,
     "expected": d(10), "created": dt(days=-25),
     "description": "Upgrade de licencias y módulo de importaciones."},
    {"key": "o10", "p": "p16", "stage": "COTIZACION", "type": "NUEVO",
     "title": "DS-CONT Team (2 PS)", "amount": 3150, "probability": 45,
     "expected": d(18), "created": dt(days=-10),
     "description": "2 puestos de trabajo con módulo de inventarios."},
]

# ─────────────────────────────────────────────────────────────────────────────
# Cotizaciones: items = (código de producto, cantidad, precio opcional)
# ─────────────────────────────────────────────────────────────────────────────
QUOTES: list[dict] = [
    {"p": "p1", "opp": "o1", "status": "SENT", "issue": d(-3), "expiration": d(2),
     "created": dt(days=-3), "updated": dt(days=-3),
     "items": [("DSCCLOUD06", 2, None), ("DSCCLOUD08", 3, None)],
     "notes": "Cotización del plan Advance anual más usuarios adicionales."},
    {"p": "p2", "opp": "o2", "status": "DRAFT", "issue": d(-1), "expiration": d(30),
     "created": dt(days=-1), "updated": dt(days=-1),
     "items": [("DSCPRO003", 1, None), ("DSCSAA0004", 2, None)],
     "notes": "Borrador para revisión con el gerente de operaciones."},
    {"p": "p3", "opp": "o3", "status": "ACCEPTED", "issue": d(-7), "expiration": d(-2),
     "created": dt(days=-7), "updated": dt(days=-2),
     "items": [("DSCSAA0001", 1, None)],
     "notes": "Renovación anual aceptada."},
    {"p": "p8", "opp": None, "status": "SENT", "issue": dt(days=-20).date(), "expiration": d(10),
     "created": dt(days=-20), "updated": dt(days=-10),
     "items": [("DSBPRO002", 1, None), ("DSBSAA010", 1, None)],
     "notes": "Cotización enviada; pendiente de respuesta."},
    {"p": "p10", "opp": "o4", "status": "SENT", "issue": d(-2), "expiration": d(5),
     "created": dt(days=-2), "updated": dt(days=-2),
     "items": [("DSCCLOUD06", 2, None), ("DSCCLOUD08", 4, None)],
     "notes": "Propuesta para 3 sedes con usuarios adicionales."},
    {"p": "p11", "opp": "o5", "status": "ACCEPTED", "issue": d(-42), "expiration": d(-30),
     "created": dt(days=-42), "updated": dt(days=-40),
     "items": [("DSCSAA0001", 1, None)],
     "notes": "Renovación anual aceptada."},
    {"p": "p12", "opp": "o6", "status": "ACCEPTED", "issue": d(-5), "expiration": d(0),
     "created": dt(days=-5), "updated": dt(hours=-4),
     "items": [("DSBPRO001", 1, None), ("DSBSAA010", 1, None)],
     "notes": "Implementación aceptada; pago confirmado."},
    {"p": "p13", "opp": "o7", "status": "REJECTED", "issue": d(-12), "expiration": d(-5),
     "created": dt(days=-12), "updated": dt(days=-8),
     "items": [("DSCPRO003", 1, None)],
     "notes": "Rechazada por precio."},
    {"p": "p14", "opp": "o8", "status": "DRAFT", "issue": d(-15), "expiration": d(15),
     "created": dt(days=-15), "updated": dt(days=-15),
     "items": [("DSCPRO001", 1, None)],
     "notes": "Borrador sin respuesta del cliente."},
    {"p": "p15", "opp": "o9", "status": "SENT", "issue": d(-15), "expiration": d(7),
     "created": dt(days=-15), "updated": dt(days=-8),
     "items": [("DSBPRO003", 1, None), ("DSBPRO004", 1, None)],
     "notes": "Upgrade de licencias; pendiente de decisión."},
    {"p": "p16", "opp": "o10", "status": "DRAFT", "issue": d(-1), "expiration": d(14),
     "created": dt(days=-1), "updated": dt(days=-1),
     "items": [("DSCPRO006", 1, None), ("DSCSAA0007", 1, None)],
     "notes": "Borrador para la demo de inventarios."},
    {"p": "p18", "opp": None, "status": "SENT", "issue": d(-30), "expiration": d(-3),
     "created": dt(days=-30), "updated": dt(days=-30),
     "items": [("DSCCLOUD04", 1, None)],
     "notes": "Cotización vencida; requiere reactivación."},
    {"p": "p2", "opp": "o2", "status": "SENT", "issue": d(-4), "expiration": d(3),
     "created": dt(days=-4), "updated": dt(days=-4),
     "items": [("DSCPRO003", 1, None)],
     "notes": "Versión de la cotización con 1 terminal; por vencer."},
]

TAG_DEFS = [
    ("VIP", "#f59e0b", "Cliente o prospecto estratégico"),
    ("Alto potencial", "#10b981", "Alta probabilidad de cierre"),
    ("Renovación próxima", "#3b82f6", "Cliente con renovación en los próximos 30 días"),
    ("Referido", "#8b5cf6", "Llegó por referencia de un cliente"),
    ("Recuperar", "#ef4444", "Requiere campaña de recuperación"),
    ("Frío", "#6b7280", "Sin interés o sin respuesta"),
]

DEMO_ROLE_CODE = "DEMO_TESTER"


def catalog_map(s) -> dict[tuple[str, str], CatalogOption]:
    rows = s.execute(
        select(CatalogOption, Catalog.code).join(Catalog, Catalog.id == CatalogOption.catalog_id)
    ).all()
    return {(catalog_code, option.code): option for option, catalog_code in rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Datos demo para Gianfranco")
    parser.add_argument("--reset", action="store_true", help="Borra los datos demo previos antes de crearlos")
    args = parser.parse_args()

    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.email == TARGET_EMAIL))
        if user is None:
            raise SystemExit(f"No existe el usuario {TARGET_EMAIL}")

        existing = s.scalar(select(func.count(Prospect.id)).where(Prospect.owner_id == user.id)) or 0
        if existing and not args.reset:
            raise SystemExit(
                f"{TARGET_EMAIL} ya tiene {existing} prospectos. Usa --reset para reemplazar los datos demo."
            )

        # ── Limpieza opcional ─────────────────────────────────────────────
        if args.reset:
            s.execute(delete(Prospect).where(Prospect.owner_id == user.id))
            s.execute(delete(Alert).where(Alert.user_id == user.id))
            s.execute(delete(Task).where(Task.assignee_id == user.id))
            s.execute(delete(Opportunity).where(Opportunity.owner_id == user.id))
            s.execute(
                delete(AuditLog).where(AuditLog.user_id == user.id, AuditLog.user_agent == "Demo seed")
            )
            s.flush()

        # ── Acceso y contraseña conocida ─────────────────────────────────
        user.password_hash = hash_password(DEMO_PASSWORD)
        user.must_change_password = False
        user.is_active = True
        user.failed_login_count = 0
        user.locked_until = None

        # Rol de demostración: mismas pantallas que gerencia, sin acceso global a prospectos.
        perms = {p.code: p for p in s.scalars(select(Permission))}
        demo_permissions = list(
            dict.fromkeys(
                [*SALES_CODES, P.DASHBOARD_MANAGEMENT, P.IMPORT_RUN, P.USERS_READ, P.ROLES_READ,
                 P.CATALOGS_MANAGE, P.SETTINGS_READ, P.AUDIT_READ]
            )
        )
        role = s.scalar(select(Role).where(Role.code == DEMO_ROLE_CODE))
        if role is None:
            role = Role(
                code=DEMO_ROLE_CODE,
                name="Demo (todas las pantallas)",
                description="Perfil de prueba con acceso a todas las pantallas, limitado a sus propios prospectos.",
                is_system=False,
            )
            s.add(role)
            s.flush()
        role.permissions = [perms[c] for c in demo_permissions if c in perms]
        if role not in user.roles:
            user.roles.append(role)
        s.flush()

        cat = catalog_map(s)
        products = {p.code: p for p in s.scalars(select(Product))}
        admin = s.get(User, ADMIN_ID)
        carla = s.scalar(select(User).where(User.email == "carla.rojas@dataservice.pe"))
        maria = s.scalar(select(User).where(User.email == "maria.quispe@dataservice.pe"))
        lucia = s.scalar(select(User).where(User.email == "lucia.fernandez@dataservice.pe"))
        gerencia = s.scalar(select(User).where(User.email == "gerencia@dataservice.pe"))

        def opt(catalog: str, code: str) -> CatalogOption:
            return cat[(catalog, code)]

        def opt_id(catalog: str, code: str | None) -> int | None:
            return opt(catalog, code).id if code else None

        # ── Etiquetas ─────────────────────────────────────────────────────
        tags: dict[str, Tag] = {}
        for name, color, description in TAG_DEFS:
            tag = s.scalar(select(Tag).where(Tag.name == name))
            if tag is None:
                tag = Tag(name=name, color=color, description=description)
                s.add(tag)
            tags[name] = tag
        s.flush()

        # ── Prospectos ───────────────────────────────────────────────────
        prospects: dict[str, Prospect] = {}
        contacts: dict[tuple[str, int], ProspectContact] = {}
        for spec in PROSPECTS:
            p = Prospect(
                code="TMP",
                person_type=spec["person_type"],
                document_type_id=opt_id("document_type", spec.get("document")),
                document_number=spec.get("document_number"),
                first_name=spec.get("first_name"),
                last_name=spec.get("last_name"),
                birth_date=spec.get("birth_date"),
                legal_name=spec.get("legal_name"),
                trade_name=spec.get("trade_name"),
                display_name=(
                    " ".join(filter(None, [spec.get("first_name"), spec.get("last_name")]))
                    if spec["person_type"] == "NATURAL"
                    else spec["legal_name"]
                ),
                email=spec.get("email"),
                phone=spec.get("phone"),
                phone_alt=spec.get("phone_alt"),
                whatsapp=spec.get("whatsapp"),
                address=spec.get("address"),
                source_id=opt_id("prospect_source", spec.get("source")),
                acquisition_channel_id=opt_id("contact_channel", spec.get("channel")),
                interest_level_id=opt_id("interest_level", spec.get("interest")),
                priority_id=opt_id("priority", spec.get("priority")),
                discard_reason_id=opt_id("discard_reason", spec.get("discard_reason")),
                relationship_type=spec["relationship"],
                status=spec["status"],
                owner_id=user.id,
                notes=spec.get("notes"),
                converted_at=spec.get("converted_at"),
                converted_by_id=user.id if spec["relationship"] == "CLIENTE" else None,
                created_at=spec["created"],
                updated_at=spec["created"],
                score=Decimal("0"),
                score_breakdown={},
                legacy_attempts=0,
            )
            p.tags = [tags[name] for name in spec.get("tags", [])]
            s.add(p)
            s.flush()
            p.code = f"PRO-{p.id:06d}"
            prospects[spec["key"]] = p

            for index, c in enumerate(spec.get("contacts", [])):
                contact = ProspectContact(
                    prospect_id=p.id,
                    full_name=c["full_name"],
                    position=c.get("position"),
                    area=c.get("area"),
                    email=c.get("email"),
                    phone=c.get("phone"),
                    whatsapp=c.get("whatsapp"),
                    is_primary=c.get("is_primary", False),
                    notes=c.get("notes"),
                    created_at=spec["created"],
                    updated_at=spec["created"],
                )
                s.add(contact)
                s.flush()
                contacts[(spec["key"], index)] = contact

            # Historial de estados
            s.add(
                ProspectStatusHistory(
                    prospect_id=p.id,
                    from_relationship_type=None,
                    to_relationship_type="PROSPECTO",
                    from_status=None,
                    to_status="ACTIVO",
                    changed_by_id=user.id,
                    reason="Creación del prospecto",
                    created_at=spec["created"],
                )
            )
            if spec.get("status") != "ACTIVO":
                s.add(
                    ProspectStatusHistory(
                        prospect_id=p.id,
                        from_relationship_type="PROSPECTO",
                        to_relationship_type="PROSPECTO",
                        from_status="ACTIVO",
                        to_status=spec["status"],
                        changed_by_id=user.id,
                        reason=spec.get("status_reason") or "Cambio de estado",
                        created_at=spec["status_changed"] or spec["created"] + timedelta(days=1),
                    )
                )
            if spec["relationship"] == "CLIENTE":
                s.add(
                    ProspectStatusHistory(
                        prospect_id=p.id,
                        from_relationship_type="PROSPECTO",
                        to_relationship_type="CLIENTE",
                        from_status="ACTIVO",
                        to_status="ACTIVO",
                        changed_by_id=user.id,
                        reason="Conversión a cliente (cotización aceptada)",
                        created_at=spec.get("converted_at") or spec["created"],
                    )
                )

            # Asignaciones
            initial_owner = user
            if spec["key"] == "p2":
                initial_owner = maria or user
            elif spec["key"] == "p10":
                initial_owner = carla or user
            elif spec["key"] == "p8":
                initial_owner = lucia or user
            s.add(
                ProspectAssignment(
                    prospect_id=p.id,
                    from_user_id=None,
                    to_user_id=initial_owner.id,
                    assigned_by_id=admin.id if admin else user.id,
                    reason="Creación del prospecto",
                    assigned_at=spec["created"],
                )
            )
            if initial_owner.id != user.id:
                s.add(
                    ProspectAssignment(
                        prospect_id=p.id,
                        from_user_id=initial_owner.id,
                        to_user_id=user.id,
                        assigned_by_id=gerencia.id if gerencia else user.id,
                        reason="Reasignación de cartera al ejecutivo Gian Franco",
                        assigned_at=spec["created"] + timedelta(days=2),
                    )
                )
        s.flush()

        # ── Interacciones ────────────────────────────────────────────────
        interactions_by_prospect: dict[str, list[Interaction]] = {}
        attempts: dict[str, int] = {}
        for item in sorted(INTERACTIONS, key=lambda x: x["at"]):
            p = prospects[item["p"]]
            attempts[item["p"]] = attempts.get(item["p"], 0) + 1
            contact = contacts.get((item["p"], item.get("contact"))) if item.get("contact") is not None else None
            interaction = Interaction(
                prospect_id=p.id,
                user_id=user.id,
                contact_id=contact.id if contact else None,
                occurred_at=item["at"],
                channel_id=opt("contact_channel", item["channel"]).id,
                mode_id=opt_id("contact_mode", item.get("mode")),
                result_id=opt("contact_result", item["result"]).id,
                interest_level_id=opt_id("interest_level", item.get("interest")),
                attempt_number=attempts[item["p"]],
                notes=item.get("notes"),
                next_action_desc=item.get("next_desc"),
                next_action_at=item.get("next"),
                stage_before="ACTIVO",
                stage_after=p.status,
                created_at=item["at"],
                updated_at=item["at"],
            )
            s.add(interaction)
            interactions_by_prospect.setdefault(item["p"], []).append(interaction)
        s.flush()

        # Resumen desnormalizado del prospecto (igual que InteractionService)
        for key, p in prospects.items():
            items = interactions_by_prospect.get(key, [])
            p.interaction_count = len(items)
            if items:
                latest = max(items, key=lambda i: i.occurred_at)
                p.first_contact_at = min(i.occurred_at for i in items)
                p.last_contact_at = latest.occurred_at
                p.last_result_id = latest.result_id
                if latest.interest_level_id:
                    p.interest_level_id = latest.interest_level_id
            else:
                p.first_contact_at = None
                p.last_contact_at = None
                p.last_result_id = None
            s.add(p)
        s.flush()

        # ── Tareas ───────────────────────────────────────────────────────
        for spec in TASKS:
            p = prospects[spec["p"]]
            task = Task(
                prospect_id=p.id,
                assignee_id=user.id,
                type_id=opt_id("task_type", spec["type"]),
                priority_id=opt_id("priority", spec["priority"]),
                title=spec["title"],
                description=spec.get("description"),
                due_at=spec.get("due"),
                remind_at=spec.get("due") - timedelta(hours=1) if spec.get("due") else None,
                status=spec["status"],
                completed_at=spec.get("completed"),
            )
            # created_at coherente: 3 días antes del vencimiento (o antes de completarse)
            base = spec.get("completed") or spec.get("due") or NOW
            task.created_at = base - timedelta(days=3)
            task.updated_at = spec.get("completed") or spec.get("due") or NOW
            s.add(task)
        s.flush()

        # ── Oportunidades ────────────────────────────────────────────────
        opps: dict[str, Opportunity] = {}
        for spec in OPPS:
            p = prospects[spec["p"]]
            opp = Opportunity(
                prospect_id=p.id,
                stage_id=opt("pipeline_stage", spec["stage"]).id,
                type_id=opt_id("opportunity_type", spec.get("type")),
                loss_reason_id=opt_id("loss_reason", spec.get("loss")),
                owner_id=user.id,
                title=spec["title"],
                description=spec.get("description"),
                estimated_amount=Decimal(str(spec["amount"])),
                probability=spec.get("probability"),
                expected_close_date=spec.get("expected"),
                actual_close_date=spec.get("actual"),
                created_at=spec["created"],
                updated_at=spec.get("actual") and datetime.combine(spec["actual"], time(18), tzinfo=UTC) or spec["created"],
            )
            s.add(opp)
            s.flush()
            opps[spec["key"]] = opp

        # ── Cotizaciones ─────────────────────────────────────────────────
        for spec in QUOTES:
            p = prospects[spec["p"]]
            quote = Quote(
                prospect_id=p.id,
                opportunity_id=opps[spec["opp"]].id if spec.get("opp") else None,
                status=spec["status"],
                issue_date=spec["issue"],
                expiration_date=spec.get("expiration"),
                notes=spec.get("notes"),
                created_at=spec["created"],
                updated_at=spec["updated"],
                subtotal=Decimal("0"),
                tax=Decimal("0"),
                total=Decimal("0"),
            )
            items: list[QuoteItem] = []
            for product_code, qty, price in spec["items"]:
                product = products[product_code]
                unit_price = Decimal(str(price)) if price is not None else Decimal(str(product.list_price))
                items.append(
                    QuoteItem(
                        product_id=product.id,
                        description=product.name,
                        quantity=qty,
                        unit_price=unit_price,
                        total=unit_price * qty,
                        created_at=spec["created"],
                        updated_at=spec["created"],
                    )
                )
            quote.items = items
            subtotal = sum((i.total for i in items), Decimal("0"))
            quote.subtotal = subtotal
            quote.tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
            quote.total = quote.subtotal + quote.tax
            s.add(quote)
        s.flush()

        # ── Score de cada prospecto ──────────────────────────────────────
        calculator = ScoreCalculator(s)
        for p in prospects.values():
            calculator.recalculate(p)
        s.flush()

        # ── Auditoría ────────────────────────────────────────────────────
        p1 = prospects["p1"]
        p3 = prospects["p3"]
        p8 = prospects["p8"]
        audit_rows = [
            ("auth.login", "user", str(user.public_id), user.full_name, dt(days=-3, hours=-2)),
            ("prospect.created", "prospect", str(p1.public_id), p1.display_name, dt(hours=-6)),
            ("prospect.created", "prospect", str(p3.public_id), p3.display_name, dt(days=-150)),
            ("prospect.assigned", "prospect", str(p8.public_id), p8.display_name, dt(days=-58)),
            ("prospect.status_changed", "prospect", str(prospects["p4"].public_id), prospects["p4"].display_name, dt(days=-12)),
            ("interaction.created", "interaction", str(p1.public_id), f"Interacción 1 - {p1.display_name}", dt(hours=-9)),
            ("task.created", "task", str(p1.public_id), "Llamar para confirmar demo", dt(hours=-5)),
            ("opportunity.created", "opportunity", str(opps["o1"].public_id), opps["o1"].title, dt(days=-8)),
            ("opportunity.won", "opportunity", str(opps["o3"].public_id), opps["o3"].title, dt(days=-2)),
            ("quote.created", "quote", str(p1.public_id), f"Cotización: {p1.display_name}", dt(days=-3)),
            ("quote.status_changed", "quote", str(p3.public_id), f"Cotización ACCEPTED: {p3.display_name}", dt(days=-2)),
            ("auth.logout", "user", str(user.public_id), user.full_name, dt(days=-1, hours=-1)),
        ]
        for action, entity_type, entity_id, label, created in audit_rows:
            s.add(
                AuditLog(
                    user_id=user.id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_label=label,
                    before=None,
                    after=None,
                    ip="127.0.0.1",
                    user_agent="Demo seed",
                    created_at=created,
                )
            )
        s.flush()
        s.commit()

        # ── Alertas automáticas ──────────────────────────────────────────
        s.refresh(user)
        generated = AlertService(s).generate_for_user(user)
        s.flush()
        s.commit()

        # Variedad de estados en alertas: algunas leídas y algunas descartadas.
        alerts = list(s.scalars(select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at)))
        no_followup_seen = 0
        quote_no_response_seen = 0
        for alert in alerts:
            if alert.alert_type == "NO_FOLLOWUP":
                no_followup_seen += 1
                if no_followup_seen == 1:
                    alert.status = "READ"
                    alert.read_at = NOW - timedelta(hours=2)
                elif no_followup_seen == 2:
                    alert.status = "DISMISSED"
                    alert.dismissed_at = NOW - timedelta(hours=1)
            elif alert.alert_type == "QUOTE_NO_RESPONSE" and quote_no_response_seen == 0:
                quote_no_response_seen += 1
                alert.status = "READ"
                alert.read_at = NOW - timedelta(hours=2)
        s.commit()

        # ── Resumen ──────────────────────────────────────────────────────
        alert_count = s.scalar(select(func.count(Alert.id)).where(Alert.user_id == user.id)) or 0
        print("=" * 64)
        print("Datos demo creados para:", user.full_name, f"<{user.email}>")
        print("Contraseña:", DEMO_PASSWORD)
        print("Prospectos:", len(prospects))
        print("Interacciones:", len(INTERACTIONS))
        print("Tareas:", len(TASKS))
        print("Oportunidades:", len(OPPS))
        print("Cotizaciones:", len(QUOTES))
        print("Alertas generadas:", alert_count)
        print("Rol adicional:", role.code, f"({len(role.permissions)} permisos)")
        print("=" * 64)


if __name__ == "__main__":
    main()
