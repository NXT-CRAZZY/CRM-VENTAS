"""Genera un Excel FOR-VEN-001 *sintético* con datos inventados (fase 0).

Reproduce la estructura descrita del informe semanal de ventas para desarrollar y probar el
importador (fase 6) sin datos reales. Incluye errores intencionales marcados en
OBSERVACIONES con el prefijo [ERROR-PRUEBA] para validar los mensajes por fila.

Uso:  python -m scripts.generate_legacy_excel [ruta_salida.xlsx]
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.seeds.data.products import PRODUCTS_PARSED
from app.shared.documents import ruc_check_digit

rng = random.Random(20261030)  # determinista: siempre el mismo archivo

COMPANIES = [
    ("Estudio Contable Huamán & Asociados S.A.C.", "Av. Arequipa 2450, Lince, Lima"),
    ("Ferretería El Constructor del Norte E.I.R.L.", "Jr. Pizarro 455, Trujillo"),
    ("Distribuidora Andina de Alimentos S.A.C.", "Calle Mercaderes 312, Arequipa"),
    ("Clínica Dental Sonrisa Plena S.A.C.", "Av. Grau 870, Piura"),
    ("Transportes Rápidos del Sur S.R.L.", "Av. de la Cultura 1120, Cusco"),
    ("Inversiones Textiles Gamarra S.A.C.", "Jr. Gamarra 1020, La Victoria, Lima"),
    ("Colegio Particular San Martín de Porres S.A.C.", "Av. Universitaria 3300, Los Olivos, Lima"),
    ("Agroexportadora Valle Verde S.A.C.", "Carretera Panamericana Norte Km 560, Chiclayo"),
    ("Consultores Tributarios Integrales S.A.C.", "Av. Javier Prado Este 1650, San Isidro, Lima"),
    ("Minimarket La Economía E.I.R.L.", "Av. Ejército 615, Yanahuara, Arequipa"),
    ("Servicios Médicos Santa Rosa S.A.C.", "Jr. Junín 288, Huancayo"),
    ("Constructora Pacífico Sur S.A.C.", "Av. Benavides 4980, Surco, Lima"),
    ("Librería y Papelería El Estudiante E.I.R.L.", "Jr. Huallaga 410, Cercado de Lima"),
    ("Hotel Mirador del Misti S.A.C.", "Calle Jerusalén 503, Arequipa"),
    ("Grifo Servicentro Los Ángeles S.R.L.", "Av. Túpac Amaru 1540, Comas, Lima"),
]
FIRST = [
    "Rosa",
    "Jorge",
    "Patricia",
    "Luis",
    "Carmen",
    "Miguel",
    "Silvia",
    "Víctor",
    "Elena",
    "Raúl",
    "Gabriela",
    "César",
]
LAST = ["Mendoza", "Torres", "Flores", "Ramírez", "Chávez", "Vargas", "Castillo", "Paredes", "Gutiérrez", "Salinas"]
CHANNELS = ["C", "T", "V", "W", "F", "R"]
INTEREST = ["ALTO", "REGULAR", "BAJO"]
NOTES = [
    "Solicita demostración del módulo de planillas.",
    "Pide cotización para 2 terminales.",
    "Volver a llamar la próxima semana, gerente de viaje.",
    "Interesado en migrar a la nube.",
    "Compara precios con otro proveedor.",
    "Renovación de licencia anual.",
    "Consulta por usuarios adicionales.",
    "No contestó, se dejó mensaje.",
]
# Productos con precio > 0 para ventas de ejemplo
SELLABLE = [p for p in PRODUCTS_PARSED if p[5] > 0]


def fake_ruc(prefix: str = "20") -> str:
    body = prefix + "".join(str(rng.randint(0, 9)) for _ in range(8))
    return body + str(ruc_check_digit(body))


def build_rows(today: datetime) -> list[dict]:
    rows: list[dict] = []
    number = 0
    for index, (name, address) in enumerate(COMPANIES):
        number += 1
        ruc = fake_ruc()
        contact = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        email = f"{contact.split()[0].lower()}@{name.split()[0].lower()}.pe".replace("í", "i").replace("é", "e")
        phone = f"9{rng.randint(10_000_000, 99_999_999)}"
        attempts = rng.randint(1, 4)
        start = (today - timedelta(days=rng.randint(6, 40))).replace(hour=0, minute=0)
        for attempt in range(1, attempts + 1):
            last = attempt == attempts
            day = min(
                start + timedelta(days=attempt * rng.randint(1, 4)), today.replace(hour=0, minute=0) - timedelta(days=1)
            )
            when = day + timedelta(hours=rng.randint(9, 17), minutes=rng.choice([0, 15, 30, 45]))
            if last and index < 3:  # algunos contactos hoy, para que el bloque HOY tenga datos
                when = today.replace(hour=9 + index, minute=15)
            result = rng.choice(["C", "D", "V"]) if last and rng.random() < 0.7 else rng.choice(["C", "D", ""])
            product = rng.choice(SELLABLE) if result == "V" else None
            rows.append(
                {
                    "number": number,
                    "ruc": ruc,
                    "name": name,
                    "address": address,
                    "contact": contact,
                    "email": email,
                    "phone": phone,
                    "channel": rng.choice(CHANNELS),
                    "when": when,
                    "mode": rng.choice(["P", "R", "R"]),
                    "attempt": attempt,
                    "interest": rng.choice(INTEREST),
                    "result": result,
                    "amount": float(product[5]) if product else None,
                    "sold": rng.choice(["A", "N"]) if product else "",
                    "notes": rng.choice(NOTES) + (f" Producto: {product[0]}" if product else ""),
                }
            )

    # ---- Errores intencionales para probar el importador ----
    bad = dict(rows[0], number=number + 1, ruc="20123456789", name="Empresa con RUC Inválido S.A.C.")
    bad["notes"] = "[ERROR-PRUEBA] RUC con dígito verificador incorrecto."
    dup = dict(rows[3], number=number + 2, name=rows[3]["name"].upper())
    dup["notes"] = "[ERROR-PRUEBA] Prospecto duplicado (mismo RUC que la fila de " + rows[3]["name"] + ")."
    bad_date = dict(
        rows[5], number=number + 3, ruc=fake_ruc(), name="Bodega Doña Julia E.I.R.L.", when="31/02/2026 10:00"
    )
    bad_date["notes"] = "[ERROR-PRUEBA] Fecha inexistente."
    no_name = dict(rows[7], number=number + 4, ruc=fake_ruc(), name="")
    no_name["notes"] = "[ERROR-PRUEBA] Falta la razón social."
    bad_amount = dict(
        rows[9],
        number=number + 5,
        ruc=fake_ruc(),
        name="Panadería San Antonio S.R.L.",
        result="V",
        amount="mil quinientos",
        sold="N",
    )
    bad_amount["notes"] = "[ERROR-PRUEBA] Monto no numérico."
    rows += [bad, dup, bad_date, no_name, bad_amount]
    return rows


def write_workbook(rows: list[dict], today: datetime, path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "INFORME SEMANAL"
    bold = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="E03E0F")
    sub_fill = PatternFill("solid", fgColor="FDE7DF")
    thin = Side(style="thin", color="BBBBBB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws["A1"] = "FOR-VEN-001 INFORME SEMANAL DE VENTAS V03 — DATOS SINTÉTICOS DE PRUEBA"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "FECHA DE INFORME:"
    ws["A2"].font = bold
    ws["C2"] = today.date()
    ws["C2"].number_format = "DD/MM/YYYY"

    # Bloque de indicadores (en el Excel original se llenaba a mano; el CRM los calculará)
    ws["A4"], ws["C4"], ws["E4"] = "INDICADOR", "HOY", "ACUMULADO DEL MES"
    ws["C5"], ws["D5"], ws["E5"], ws["F5"] = "ACTUALIZACIÓN", "NUEVOS CLIENTES", "ACTUALIZACIÓN", "NUEVOS CLIENTES"
    ws["A6"], ws["A7"] = "TOTAL DE COTIZACIONES", "TOTAL DE VENTAS"
    month_rows = [r for r in rows if isinstance(r["when"], datetime) and r["when"].month == today.month]
    today_rows = [r for r in month_rows if r["when"].date() == today.date()]
    for col, subset, sold in (
        ("C", today_rows, "A"),
        ("D", today_rows, "N"),
        ("E", month_rows, "A"),
        ("F", month_rows, "N"),
    ):
        ws[f"{col}6"] = sum(1 for r in subset if r["result"] == "C")
        ws[f"{col}7"] = sum(
            r["amount"] for r in subset if r["result"] == "V" and r["sold"] == sold and isinstance(r["amount"], float)
        )
        ws[f"{col}7"].number_format = '"S/" #,##0.00'
    for row in ws["A4:F7"]:
        for cell in row:
            cell.border = border
            cell.alignment = center
    for cell in ("A4", "C4", "E4", "C5", "D5", "E5", "F5"):
        ws[cell].font = bold
        ws[cell].fill = sub_fill
    ws.merge_cells("A4:B5")
    ws.merge_cells("C4:D4")
    ws.merge_cells("E4:F4")
    ws.merge_cells("A6:B6")
    ws.merge_cells("A7:B7")

    headers = [
        "N°",
        "RUC",
        "RAZÓN SOCIAL",
        "DIRECCIÓN",
        "PERSONA DE CONTACTO",
        "CORREO ELECTRÓNICO",
        "TELÉFONO",
        "FORMA DE CONTACTO",
        "FECHA Y HORA DE CONTACTO",
        "CONTACTO",
        "NRO DE VECES DE INTENTO DE CONTACTO",
        "NIVEL DE INTERÉS",
        "LOGRO DEL CONTACTO",
        "MONTO DE VENTA",
        "PRODUCTO VENDIDO",
        "OBSERVACIONES",
    ]
    start = 9
    for i, h in enumerate(headers, start=1):
        cell = ws.cell(row=start, column=i, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border
    for offset, r in enumerate(rows, start=1):
        values = [
            r["number"],
            r["ruc"],
            r["name"],
            r["address"],
            r["contact"],
            r["email"],
            r["phone"],
            r["channel"],
            r["when"],
            r["mode"],
            r["attempt"],
            r["interest"],
            r["result"],
            r["amount"],
            r["sold"],
            r["notes"],
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=start + offset, column=col, value=value)
            cell.border = border
            if col == 9 and isinstance(value, datetime):
                cell.number_format = "DD/MM/YYYY HH:MM"
            if col == 14 and isinstance(value, float):
                cell.number_format = '"S/" #,##0.00'

    widths = [5, 13, 42, 40, 22, 30, 12, 10, 18, 10, 14, 12, 12, 14, 11, 60]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=start + 1, column=4)

    legend = wb.create_sheet("CÓDIGOS")
    legend.append(["CAMPO", "CÓDIGO", "SIGNIFICADO"])
    for item in [
        ("FORMA DE CONTACTO", "C", "Correo"),
        ("FORMA DE CONTACTO", "T", "Teléfono"),
        ("FORMA DE CONTACTO", "V", "Visita"),
        ("FORMA DE CONTACTO", "W", "Web"),
        ("FORMA DE CONTACTO", "F", "Facebook"),
        ("FORMA DE CONTACTO", "R", "Referencia de otro cliente"),
        ("CONTACTO", "P", "Presencial"),
        ("CONTACTO", "R", "Remoto"),
        ("LOGRO DEL CONTACTO", "C", "Cotización"),
        ("LOGRO DEL CONTACTO", "D", "Demostración"),
        ("LOGRO DEL CONTACTO", "V", "Venta"),
        ("PRODUCTO VENDIDO", "A", "Actualización"),
        ("PRODUCTO VENDIDO", "N", "Nuevo"),
        ("NIVEL DE INTERÉS", "ALTO / REGULAR / BAJO", "Pendiente confirmar códigos reales del Excel original"),
    ]:
        legend.append(item)
    for cell in legend[1]:
        cell.font = bold
    legend.column_dimensions["A"].width = 22
    legend.column_dimensions["B"].width = 24
    legend.column_dimensions["C"].width = 50

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> None:
    default = Path(__file__).resolve().parents[3] / "docs" / "fase-0" / "FOR-VEN-001_demo.xlsx"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    today = datetime(2026, 10, 30, 12, 0)
    rows = build_rows(today)
    write_workbook(rows, today, out)
    print(f"Excel sintético generado: {out} ({len(rows)} filas, {len(COMPANIES)} prospectos + 5 filas con errores)")


if __name__ == "__main__":
    main()
