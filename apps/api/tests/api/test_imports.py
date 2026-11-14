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


def _won_opportunity(client: TestClient, headers: dict, prospect_id: str, amount: float, type_code: str | None) -> dict:
    from tests.api.test_opportunities import _stage_id, _type_id

    body = {
        "prospect_id": prospect_id,
        "title": "Venta sin cotización",
        "stage_id": _stage_id(client, headers, "CERRADO_GANADO"),
        "estimated_amount": amount,
    }
    if type_code:
        body["type_id"] = _type_id(client, headers, type_code)
    r = client.post(f"{API}/opportunities", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _row(report: dict, label: str) -> dict:
    return next(r for r in report["rows"] if r["label"].strip() == label)


def test_weekly_report_sales_from_all_won_opportunities(client: TestClient, admin_headers: dict) -> None:
    from tests.api.test_interactions import _create_prospect

    def report() -> dict:
        r = client.get(f"{API}/reports/weekly", headers=admin_headers)
        assert r.status_code == 200, r.text
        return r.json()

    before = report()
    prospect = _create_prospect(client, admin_headers)
    _won_opportunity(client, admin_headers, prospect["id"], 1000, "NUEVO")
    _won_opportunity(client, admin_headers, prospect["id"], 250, "ACTUALIZACION")
    after = report()

    total_b, total_a = _row(before, "Ventas totales"), _row(after, "Ventas totales")
    assert total_a["today"] - total_b["today"] == 1250
    # el desglose por tipo siempre suma el total
    type_rows = [r for r in after["rows"] if r["label"].startswith("   ")]
    assert round(sum(r["month"] for r in type_rows), 2) == round(total_a["month"], 2)
    # ganar una oportunidad convierte al prospecto en cliente y cuenta como nuevo cliente
    assert _row(after, "Nuevos clientes")["today"] - _row(before, "Nuevos clientes")["today"] == 1


def test_weekly_report_seller_sees_only_own(
    client: TestClient, admin_headers: dict, sales_headers: dict
) -> None:
    from tests.api.test_interactions import _create_prospect

    prospect = _create_prospect(client, admin_headers)
    _won_opportunity(client, admin_headers, prospect["id"], 777, "NUEVO")

    admin_total = _row(client.get(f"{API}/reports/weekly", headers=admin_headers).json(), "Ventas totales")["today"]
    seller_total = _row(client.get(f"{API}/reports/weekly", headers=sales_headers).json(), "Ventas totales")["today"]
    assert admin_total >= 777
    assert seller_total < admin_total  # el vendedor no ve las ventas de otros


def test_weekly_report_filters_and_detail(client: TestClient, admin_headers: dict) -> None:
    from tests.api.test_interactions import _create_prospect
    from tests.api.test_opportunities import _type_id

    prospect = _create_prospect(client, admin_headers)
    _won_opportunity(client, admin_headers, prospect["id"], 3000, "USUARIOS_ADICIONALES")
    today = date.today().isoformat()
    type_id = _type_id(client, admin_headers, "USUARIOS_ADICIONALES")

    # filtro por tipo: solo cuenta las ventas de ese tipo
    r = client.get(f"{API}/reports/weekly", params={"type_id": type_id}, headers=admin_headers)
    assert r.status_code == 200, r.text
    rep = r.json()
    total = next(x for x in rep["rows"] if x["label"] == "Ventas totales")
    assert total["today"] >= 3000
    assert total["today"] == next(x for x in rep["rows"] if x["label"].strip() == "Usuarios o terminales adicionales")["today"]

    # rango de fechas: aparece la columna extra y las etiquetas
    r = client.get(f"{API}/reports/weekly", params={"date_from": today, "date_to": today}, headers=admin_headers)
    rep = r.json()
    assert rep["range_label"] is not None
    assert next(x for x in rep["rows"] if x["label"] == "Ventas totales")["range"] >= 3000

    # rango invertido => error claro
    r = client.get(f"{API}/reports/weekly", params={"date_from": "2026-02-10", "date_to": "2026-02-01"}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_RANGE"

    # detalle: lista las ventas que componen el número
    r = client.get(
        f"{API}/reports/weekly/detail", params={"key": "sales", "period": "today", "type_id": type_id}, headers=admin_headers
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert any(i["prospect_id"] == prospect["id"] and i["amount"] == 3000 for i in items)
    assert all("sin cotización" in i["status"] or "con cotización" in i["status"] for i in items)

    # el Excel respeta los mismos filtros y se descarga
    r = client.get(f"{API}/reports/weekly/export", params={"type_id": type_id}, headers=admin_headers)
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_weekly_export_reflects_filters(client: TestClient, admin_headers: dict) -> None:
    from io import BytesIO

    from openpyxl import load_workbook

    from tests.api.test_interactions import _create_prospect
    from tests.api.test_opportunities import _type_id

    prospect = _create_prospect(client, admin_headers)
    _won_opportunity(client, admin_headers, prospect["id"], 4321, "CAMBIO_PLAN")
    _won_opportunity(client, admin_headers, prospect["id"], 111, "NUEVO")
    today = date.today().isoformat()
    type_id = _type_id(client, admin_headers, "CAMBIO_PLAN")

    r = client.get(
        f"{API}/reports/weekly/export",
        params={"date_from": today, "date_to": today, "type_id": type_id},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    wb = load_workbook(BytesIO(r.content))
    assert wb.sheetnames == ["Resumen", "Cotizaciones", "Ventas", "Nuevos clientes"]
    sales = wb["Ventas"]
    amounts = [sales.cell(row=i, column=9).value for i in range(5, sales.max_row + 1) if isinstance(sales.cell(row=i, column=1).value, int)]
    assert 4321 in amounts and 111 not in amounts  # el filtro por tipo llega al Excel
    assert sales.cell(row=sales.max_row, column=9).value == sum(amounts)
    summary = [str(c.value) for row in wb["Resumen"].iter_rows() for c in row if c.value]
    assert any("Cambio de plan" in v for v in summary)
