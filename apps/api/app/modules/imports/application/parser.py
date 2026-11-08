from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


# Columnas esperadas del FOR-VEN-001 (índice 0-based)
COL_NUMBER = 0
COL_RUC = 1
COL_NAME = 2
COL_ADDRESS = 3
COL_CONTACT = 4
COL_EMAIL = 5
COL_PHONE = 6
COL_CHANNEL = 7
COL_WHEN = 8
COL_MODE = 9
COL_ATTEMPT = 10
COL_INTEREST = 11
COL_RESULT = 12
COL_AMOUNT = 13
COL_SOLD = 14
COL_NOTES = 15


def _cell_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def _parse_when(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
    return None


def _parse_amount(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("S/", "").replace(",", "").replace(" ", "").strip()
        try:
            return float(Decimal(cleaned))
        except (InvalidOperation, ValueError):
            return None
    return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _find_header_row(ws) -> int | None:
    for idx, row in enumerate(ws.iter_rows(max_row=min(ws.max_row, 30)), start=1):
        values = [c.value for c in row[:16]]
        number = str(values[COL_NUMBER] or "").strip().upper()
        ruc = str(values[COL_RUC] or "").strip().upper()
        name = str(values[COL_NAME] or "").strip().upper()
        # Detecta encabezado sin depender de tildes/ordinal: RUC + (N°/Nro/Nro.) + Razon Social
        number_ok = ruc == "RUC" and ("N" in number or "NRO" in number or "NO" in number or number in ("#", "NUMERO", "NUM"))
        name_ok = ruc == "RUC" and ("RAZON" in name or "SOCIAL" in name or "NOMBRE" in name)
        if number_ok or name_ok:
            return idx
    return None


def parse_for_ven_001(path: Path) -> tuple[list[dict], list[str]]:
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    sheet_name = ws.title

    header_row = _find_header_row(ws)
    if header_row is None:
        return [], ["No se encontró la fila de encabezados del FOR-VEN-001 (N°, RUC, RAZÓN SOCIAL)."]

    rows: list[dict] = []
    for idx, raw in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
        values = list(raw) + [None] * (16 - len(raw))
        number = _as_int(values[COL_NUMBER])
        if number is None and not any(values[:16]):
            continue

        rows.append(
            {
                "row_number": idx,
                "number": number,
                "ruc": _cell_value(values[COL_RUC]),
                "name": _cell_value(values[COL_NAME]),
                "address": _cell_value(values[COL_ADDRESS]),
                "contact": _cell_value(values[COL_CONTACT]),
                "email": _cell_value(values[COL_EMAIL]),
                "phone": _cell_value(values[COL_PHONE]),
                "channel_code": _cell_value(values[COL_CHANNEL]),
                "when": _parse_when(values[COL_WHEN]),
                "mode_code": _cell_value(values[COL_MODE]),
                "attempt": _as_int(values[COL_ATTEMPT]),
                "interest_code": _cell_value(values[COL_INTEREST]),
                "result_code": _cell_value(values[COL_RESULT]),
                "amount": _parse_amount(values[COL_AMOUNT]),
                "sold_code": _cell_value(values[COL_SOLD]),
                "notes": _cell_value(values[COL_NOTES]),
            }
        )
    return rows, []
