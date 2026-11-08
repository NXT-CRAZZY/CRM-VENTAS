from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import API


def _build_xlsx(tmp_path: Path) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "INFORME SEMANAL"
    ws["A1"] = "FOR-VEN-001 INFORME SEMANAL DE VENTAS V03"
    ws["A2"] = "FECHA DE INFORME:"
    ws["C2"] = date.today()

    headers = [
        "N°", "RUC", "RAZÓN SOCIAL", "DIRECCIÓN", "PERSONA DE CONTACTO",
        "CORREO ELECTRÓNICO", "TELÉFONO", "FORMA DE CONTACTO", "FECHA Y HORA DE CONTACTO",
        "CONTACTO", "NRO DE VECES DE INTENTO DE CONTACTO", "NIVEL DE INTERÉS",
        "LOGRO DEL CONTACTO", "MONTO DE VENTA", "PRODUCTO VENDIDO", "OBSERVACIONES",
    ]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=9, column=i, value=h)

    rows = [
        [1, "20291417770", "Empresa de Prueba S.A.C.", "Av. Test 123", "Juan Pérez",
         "juan@test.pe", "987654321", "T", datetime(2026, 10, 30, 10, 0), "R",
         1, "ALTO", "C", None, "", "Primera llamada"],
        [2, "20291417770", "Empresa de Prueba S.A.C.", "Av. Test 123", "Juan Pérez",
         "juan@test.pe", "987654321", "T", datetime(2026, 10, 30, 11, 0), "R",
         2, "ALTO", "V", 1500.0, "N", "Venta cerrada"],
        [3, "20123456789", "Empresa con RUC Inválido S.A.C.", "", "",
         "", "", "", "", "", "", "", "", "", "", "RUC inválido"],
    ]
    for offset, row in enumerate(rows, start=1):
        for col, value in enumerate(row, start=1):
            ws.cell(row=9 + offset, column=col, value=value)

    path = tmp_path / "test_import.xlsx"
    wb.save(path)
    return path


def test_preview_for_ven_001(client: TestClient, admin_headers: dict, tmp_path: Path) -> None:
    path = _build_xlsx(tmp_path)
    with path.open("rb") as f:
        r = client.post(f"{API}/imports/for-ven-001/preview", files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 2
    assert data["invalid_rows"] == 1
    invalid = [row for row in data["rows"] if not row["valid"]]
    assert len(invalid) == 1
    assert "RUC" in invalid[0]["errors"][0]


def test_import_for_ven_001(client: TestClient, admin_headers: dict, tmp_path: Path) -> None:
    path = _build_xlsx(tmp_path)
    with path.open("rb") as f:
        r = client.post(f"{API}/imports/for-ven-001", files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, headers=admin_headers)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "COMPLETED_WITH_ERRORS"
    assert data["created_prospects"] == 1
    assert data["created_interactions"] == 2
    assert data["created_opportunities"] == 1
    assert len(data["errors"]) == 1


def test_weekly_report(client: TestClient, admin_headers: dict) -> None:
    today = date.today().isoformat()
    r = client.get(f"{API}/reports/weekly", params={"date": today}, headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "quotes_today" in data
    assert "sales_month" in data
    assert len(data["rows"]) >= 4
