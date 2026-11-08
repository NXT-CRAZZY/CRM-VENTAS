from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.api.test_interactions import _create_prospect
from tests.conftest import API


def _stage_id(client: TestClient, headers: dict, code: str) -> str:
    r = client.get(f"{API}/catalogs/bundle", params={"codes": "pipeline_stage,opportunity_type"}, headers=headers)
    assert r.status_code == 200, r.text
    return next(o["id"] for o in r.json()["catalogs"]["pipeline_stage"] if o["code"] == code)


def _type_id(client: TestClient, headers: dict, code: str) -> str:
    r = client.get(f"{API}/catalogs/bundle", params={"codes": "pipeline_stage,opportunity_type"}, headers=headers)
    assert r.status_code == 200, r.text
    return next(o["id"] for o in r.json()["catalogs"]["opportunity_type"] if o["code"] == code)


def test_create_and_list_opportunities(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    stage = _stage_id(client, admin_headers, "NUEVO")
    r = client.post(
        f"{API}/opportunities",
        json={
            "prospect_id": prospect["id"],
            "title": "Venta de servicios cloud",
            "stage_id": stage,
            "estimated_amount": 15000,
            "probability": 30,
            "expected_close_date": (date.today() + timedelta(days=15)).isoformat(),
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Venta de servicios cloud"
    assert data["stage"]["code"] == "NUEVO"

    r = client.get(f"{API}/opportunities", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1


def test_update_opportunity_stage(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    stage_new = _stage_id(client, admin_headers, "NUEVO")
    stage_quote = _stage_id(client, admin_headers, "COTIZACION")
    r = client.post(
        f"{API}/opportunities",
        json={"prospect_id": prospect["id"], "title": "Renovación anual", "stage_id": stage_new},
        headers=admin_headers,
    )
    opp_id = r.json()["id"]

    r = client.patch(f"{API}/opportunities/{opp_id}", json={"stage_id": stage_quote, "probability": 50}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["stage"]["code"] == "COTIZACION"
    assert r.json()["probability"] == 50


def test_delete_opportunity(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    stage = _stage_id(client, admin_headers, "NUEVO")
    r = client.post(
        f"{API}/opportunities",
        json={"prospect_id": prospect["id"], "title": "Oportunidad a eliminar", "stage_id": stage},
        headers=admin_headers,
    )
    opp_id = r.json()["id"]

    r = client.delete(f"{API}/opportunities/{opp_id}", headers=admin_headers)
    assert r.status_code == 204, r.text

    r = client.get(f"{API}/opportunities", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 0
