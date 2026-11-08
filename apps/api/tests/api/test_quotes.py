from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.api.test_interactions import _create_prospect
from tests.conftest import API


def _product(client: TestClient, headers: dict) -> dict:
    r = client.get(f"{API}/products", headers=headers, params={"page_size": 1})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) > 0, "Se necesita al menos un producto de semilla"
    return items[0]


def test_create_quote_and_list(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    product = _product(client, admin_headers)
    r = client.post(
        f"{API}/quotes",
        json={
            "prospect_id": prospect["id"],
            "issue_date": date.today().isoformat(),
            "expiration_date": (date.today() + timedelta(days=7)).isoformat(),
            "items": [
                {
                    "product_id": product["id"],
                    "description": product["name"],
                    "quantity": 2,
                    "unit_price": float(product["list_price"]),
                }
            ],
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "DRAFT"
    assert len(data["items"]) == 1
    assert float(data["total"]) > 0

    r = client.get(f"{API}/quotes", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1


def test_accept_quote_converts_prospect(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    product = _product(client, admin_headers)
    r = client.post(
        f"{API}/quotes",
        json={
            "prospect_id": prospect["id"],
            "issue_date": date.today().isoformat(),
            "items": [{"description": product["name"], "quantity": 1, "unit_price": 1000}],
        },
        headers=admin_headers,
    )
    quote_id = r.json()["id"]

    r = client.patch(f"{API}/quotes/{quote_id}/status", json={"status": "ACCEPTED"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ACCEPTED"

    r = client.get(f"{API}/prospects/{prospect['id']}", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["relationship_type"] == "CLIENTE"
