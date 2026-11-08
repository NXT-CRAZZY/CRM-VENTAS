from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.prospects.infrastructure.models import Prospect
from tests.api.test_interactions import _create_prospect
from tests.api.test_quotes import _product
from tests.conftest import API


def _catalog_option_id(client: TestClient, headers: dict, catalog_code: str, option_code: str) -> str:
    r = client.get(
        f"{API}/catalogs/bundle",
        params={"codes": f"{catalog_code},interest_level,priority"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    option = next(o for o in r.json()["catalogs"][catalog_code] if o["code"] == option_code)
    return option["id"]


def test_generate_alerts_requires_permission(client: TestClient, sales_headers: dict) -> None:
    r = client.post(f"{API}/alerts/generate", headers=sales_headers)
    assert r.status_code == 200, r.text


def test_generate_no_first_contact_alert(client: TestClient, admin_headers: dict, db: Session) -> None:
    prospect = _create_prospect(client, admin_headers)
    # Forzar created_at viejo directamente en BD
    p = db.scalar(select(Prospect).where(Prospect.public_id == prospect["id"]))
    assert p is not None
    p.created_at = datetime.now(UTC) - timedelta(hours=48)
    db.add(p)
    db.commit()

    r = client.post(f"{API}/alerts/generate", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json() >= 1

    r = client.get(f"{API}/alerts", headers=admin_headers)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert any(a["alert_type"] == "NO_FIRST_CONTACT" for a in items)


def test_generate_quote_expiring_alert(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    product = _product(client, admin_headers)
    r = client.post(
        f"{API}/quotes",
        json={
            "prospect_id": prospect["id"],
            "issue_date": (datetime.now(UTC) - timedelta(days=2)).date().isoformat(),
            "expiration_date": (datetime.now(UTC) + timedelta(days=1)).date().isoformat(),
            "items": [
                {
                    "product_id": product["id"],
                    "description": product["name"],
                    "quantity": 1,
                    "unit_price": 100,
                }
            ],
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    quote = r.json()

    # Enviar cotización para que entre en la alerta
    r = client.patch(f"{API}/quotes/{quote['id']}/status", json={"status": "SENT"}, headers=admin_headers)
    assert r.status_code == 200, r.text

    r = client.post(f"{API}/alerts/generate", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json() >= 1

    r = client.get(f"{API}/alerts", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert any(a["alert_type"] == "QUOTE_EXPIRING" for a in r.json()["items"])


def test_dismiss_alert(client: TestClient, admin_headers: dict, db: Session) -> None:
    prospect = _create_prospect(client, admin_headers)
    p = db.scalar(select(Prospect).where(Prospect.public_id == prospect["id"]))
    assert p is not None
    p.created_at = datetime.now(UTC) - timedelta(hours=48)
    db.add(p)
    db.commit()

    r = client.post(f"{API}/alerts/generate", headers=admin_headers)
    assert r.status_code == 200, r.text

    r = client.get(f"{API}/alerts", headers=admin_headers)
    alert_id = r.json()["items"][0]["id"]

    r = client.patch(f"{API}/alerts/{alert_id}/dismiss", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "DISMISSED"

    r = client.get(f"{API}/alerts", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert alert_id not in [a["id"] for a in r.json()["items"]]


def test_unread_count(client: TestClient, admin_headers: dict, db: Session) -> None:
    prospect = _create_prospect(client, admin_headers)
    p = db.scalar(select(Prospect).where(Prospect.public_id == prospect["id"]))
    assert p is not None
    p.created_at = datetime.now(UTC) - timedelta(hours=48)
    db.add(p)
    db.commit()

    r = client.post(f"{API}/alerts/generate", headers=admin_headers)
    assert r.status_code == 200, r.text

    r = client.get(f"{API}/alerts/unread-count", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json() >= 1
