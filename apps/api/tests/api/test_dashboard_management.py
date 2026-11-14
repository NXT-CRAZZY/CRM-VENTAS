from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.api.test_interactions import _create_prospect
from tests.api.test_opportunities import _stage_id, _type_id
from tests.conftest import API


def test_management_dashboard_requires_permission(client: TestClient, sales_headers: dict) -> None:
    r = client.get(f"{API}/dashboard/management", headers=sales_headers)
    assert r.status_code == 403, r.text


def test_management_dashboard_pipeline_and_sales(client: TestClient, manager_headers: dict) -> None:
    prospect = _create_prospect(client, manager_headers)
    stage_new = _stage_id(client, manager_headers, "NUEVO")
    stage_won = _stage_id(client, manager_headers, "CERRADO_GANADO")

    r = client.post(
        f"{API}/opportunities",
        json={
            "prospect_id": prospect["id"],
            "title": "Venta gerencial",
            "stage_id": stage_new,
            "type_id": _type_id(client, manager_headers, "NUEVO"),
            "estimated_amount": 5000,
            "expected_close_date": (date.today() + timedelta(days=5)).isoformat(),
        },
        headers=manager_headers,
    )
    assert r.status_code == 201, r.text

    r = client.get(f"{API}/dashboard/management", headers=manager_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "pipeline" in body
    assert "conversion" in body
    assert "top_performers" in body
    assert "top_products" in body
    assert body["sales_this_month"] >= 0

    # Reobtener la oportunidad creada
    r = client.get(f"{API}/opportunities", headers=manager_headers)
    opp = r.json()["items"][0]

    r = client.patch(
        f"{API}/opportunities/{opp['id']}",
        json={"stage_id": stage_won, "actual_close_date": date.today().isoformat()},
        headers=manager_headers,
    )
    assert r.status_code == 200, r.text

    r = client.get(f"{API}/dashboard/management", headers=manager_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sales_this_month"] >= 5000
    assert any(p["stage_code"] == "CERRADO_GANADO" and p["count"] >= 1 for p in body["pipeline"])
