from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.infrastructure.models import AuditLog
from tests.conftest import API

# ---------- Catálogos ----------


def test_bundle_has_legacy_excel_codes(client: TestClient, sales_headers: dict[str, str]) -> None:
    r = client.get(f"{API}/catalogs/bundle", params={"codes": "contact_channel,contact_mode"}, headers=sales_headers)
    assert r.status_code == 200
    data = r.json()["catalogs"]
    assert set(data) == {"contact_channel", "contact_mode"}
    legacy = {o["legacy_code"]: o["name"] for o in data["contact_channel"] if o["legacy_code"]}
    assert legacy == {
        "C": "Correo",
        "T": "Teléfono",
        "V": "Visita presencial",
        "W": "Formulario web",
        "F": "Messenger / Facebook",
    }
    assert {o["legacy_code"] for o in data["contact_mode"]} == {"P", "R"}


def test_opportunity_type_maps_legacy_a_n(client: TestClient, sales_headers: dict[str, str]) -> None:
    data = client.get(f"{API}/catalogs/bundle", params={"codes": "opportunity_type"}, headers=sales_headers).json()
    options = data["catalogs"]["opportunity_type"]
    assert {o["legacy_code"]: o["code"] for o in options if o["legacy_code"]} == {
        "A": "ACTUALIZACION",
        "N": "NUEVO",
    }
    assert {o["code"] for o in options} == {
        "NUEVO", "ACTUALIZACION", "USUARIOS_ADICIONALES", "CAMBIO_PLAN",
    }


def test_sales_cannot_manage_catalogs(client: TestClient, sales_headers: dict[str, str]) -> None:
    assert client.get(f"{API}/catalogs", headers=sales_headers).status_code == 403


def test_create_update_and_reorder_option(client: TestClient, db: Session, admin_headers: dict[str, str]) -> None:
    r = client.post(
        f"{API}/catalogs/prospect_source/options",
        json={"name": "Instagram", "color": "#E03E0F"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    option = r.json()
    assert option["code"] == "INSTAGRAM"
    assert option["color"] is None  # el catálogo de origen no usa color

    dup = client.post(f"{API}/catalogs/prospect_source/options", json={"name": "instagram"}, headers=admin_headers)
    assert dup.status_code == 409

    r = client.patch(f"{API}/catalog-options/{option['id']}", json={"is_active": False}, headers=admin_headers)
    assert r.json()["is_active"] is False
    bundle = client.get(f"{API}/catalogs/bundle", params={"codes": "prospect_source"}, headers=admin_headers).json()
    assert "INSTAGRAM" not in {o["code"] for o in bundle["catalogs"]["prospect_source"]}

    options = client.get(f"{API}/catalogs/prospect_source/options", headers=admin_headers).json()
    reversed_ids = [o["id"] for o in reversed(options)]
    r = client.put(f"{API}/catalogs/prospect_source/order", json={"option_ids": reversed_ids}, headers=admin_headers)
    assert [o["id"] for o in r.json()] == reversed_ids
    assert db.scalar(select(AuditLog).where(AuditLog.action == "catalog_option.updated")) is not None


def test_system_option_protected(client: TestClient, admin_headers: dict[str, str]) -> None:
    options = client.get(f"{API}/catalogs/document_type/options", headers=admin_headers).json()
    ruc = next(o for o in options if o["code"] == "RUC")
    r = client.patch(f"{API}/catalog-options/{ruc['id']}", json={"is_active": False}, headers=admin_headers)
    assert r.json()["error"]["code"] == "SYSTEM_OPTION"
    r = client.patch(f"{API}/catalog-options/{ruc['id']}", json={"name": "RUC (SUNAT)"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["name"] == "RUC (SUNAT)"


# ---------- Productos ----------


def test_seed_loads_31_products_with_exact_prices(client: TestClient, sales_headers: dict[str, str]) -> None:
    r = client.get(f"{API}/products", params={"page_size": 100}, headers=sales_headers)
    body = r.json()
    assert body["total"] == 31
    prices = {p["code"]: Decimal(p["list_price"]) for p in body["items"]}
    assert prices["DSCPRO001"] == Decimal("1470.00")
    assert prices["DSBPRO005"] == Decimal("14300.00")
    assert prices["DSCSAA0004"] == Decimal("350.00")
    assert prices["DSCCLOUD00"] == Decimal("0.00")
    assert prices["DSCCLOUD08"] == Decimal("200.00")
    assert sum(prices.values()) == Decimal("70230.00")

    categories = client.get(f"{API}/product-categories", headers=sales_headers).json()
    assert [c["product_count"] for c in categories] == [4, 6, 5, 5, 2, 9]


def test_product_filters(client: TestClient, sales_headers: dict[str, str]) -> None:
    cloud = client.get(f"{API}/products", params={"product_line": "DSCONT CLOUD"}, headers=sales_headers).json()
    assert cloud["total"] == 9
    found = client.get(f"{API}/products", params={"q": "dsbsaa01"}, headers=sales_headers).json()
    assert found["total"] == 7


def test_product_management_permissions_and_audit(
    client: TestClient, db: Session, admin_headers: dict[str, str], sales_headers: dict[str, str]
) -> None:
    product = client.get(f"{API}/products", params={"q": "DSCPRO001"}, headers=admin_headers).json()["items"][0]
    assert (
        client.patch(f"{API}/products/{product['id']}", json={"list_price": "1"}, headers=sales_headers).status_code
        == 403
    )

    r = client.patch(f"{API}/products/{product['id']}", json={"list_price": "1520.00"}, headers=admin_headers)
    assert Decimal(r.json()["list_price"]) == Decimal("1520.00")
    log = db.scalar(select(AuditLog).where(AuditLog.action == "product.price_changed"))
    assert log.before == {"list_price": "1470.00"} and log.after == {"list_price": "1520.00"}


def test_create_product_validates_and_rejects_duplicates(client: TestClient, admin_headers: dict[str, str]) -> None:
    category = client.get(f"{API}/product-categories", headers=admin_headers).json()[0]
    payload = {
        "code": "dscpro001",
        "name": "Duplicado",
        "category_id": category["id"],
        "kind": "LICENCIA_PERPETUA",
        "billing_period": "UNICO",
        "list_price": "100.00",
    }
    assert client.post(f"{API}/products", json=payload, headers=admin_headers).status_code == 409
    payload |= {"code": "DSCPRO099", "list_price": "-5"}
    assert client.post(f"{API}/products", json=payload, headers=admin_headers).status_code == 422
    payload |= {"list_price": "999.90"}
    r = client.post(f"{API}/products", json=payload, headers=admin_headers)
    assert r.status_code == 201 and r.json()["code"] == "DSCPRO099"


# ---------- Configuración y auditoría ----------


def test_settings_defaults_update_and_validation(
    client: TestClient, admin_headers: dict[str, str], manager_headers: dict[str, str]
) -> None:
    groups = {g["key"]: g for g in client.get(f"{API}/settings", headers=admin_headers).json()}
    assert groups["alerts"]["value"]["no_followup_days"] == 7
    assert groups["general"]["value"]["currency"] == "PEN"

    r = client.put(f"{API}/settings/alerts", json={"no_followup_days": 10}, headers=admin_headers)
    assert r.json()["value"]["no_followup_days"] == 10
    assert r.json()["value"]["uncontacted_hours"] == 24

    bad = client.put(f"{API}/settings/alerts", json={"no_followup_days": 0}, headers=admin_headers)
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "VALIDATION_ERROR"

    assert client.get(f"{API}/settings", headers=manager_headers).status_code == 200
    assert client.put(f"{API}/settings/alerts", json={}, headers=manager_headers).status_code == 403


def test_audit_log_filters(client: TestClient, admin_headers: dict[str, str], sales_headers: dict[str, str]) -> None:
    client.put(f"{API}/settings/general", json={"company_name": "DATA SERVICE SAC"}, headers=admin_headers)
    r = client.get(f"{API}/audit-logs", params={"action": "settings."}, headers=admin_headers)
    items = r.json()["items"]
    assert items and items[0]["after"] == {"company_name": "DATA SERVICE SAC"}
    assert items[0]["user"]["full_name"] == "Administrador del sistema"
    assert client.get(f"{API}/audit-logs", headers=sales_headers).status_code == 403
