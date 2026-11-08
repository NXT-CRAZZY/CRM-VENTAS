from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.prospects.infrastructure.models import Prospect
from tests.conftest import PASSWORD, login


def _create_natural(client: TestClient, headers: dict, **overrides) -> dict:
    payload = {
        "person_type": "NATURAL",
        "first_name": "Juan",
        "last_name": "Pérez",
        "document_number": "12345678",
        "email": "juan.perez@test.pe",
        "phone": "999888777",
        "owner_id": None,
    }
    payload.update(overrides)
    r = client.post("/api/v1/prospects", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _create_juridica(client: TestClient, headers: dict, **overrides) -> dict:
    payload = {
        "person_type": "JURIDICA",
        "legal_name": "Servicios Contables SAC",
        "trade_name": "Servicon",
        "document_number": "20131312955",
        "email": "contacto@servicon.pe",
        "phone": "012345678",
        "owner_id": None,
    }
    payload.update(overrides)
    r = client.post("/api/v1/prospects", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_natural_prospect(client: TestClient, admin_headers: dict, db: Session) -> None:
    data = _create_natural(client, admin_headers)
    assert data["person_type"] == "NATURAL"
    assert data["display_name"] == "Juan Pérez"
    assert data["code"].startswith("PRO-")


def test_create_juridica_prospect(client: TestClient, admin_headers: dict) -> None:
    data = _create_juridica(client, admin_headers)
    assert data["person_type"] == "JURIDICA"
    assert data["display_name"] == "Servicios Contables SAC"


def test_invalid_ruc_rejected(client: TestClient, admin_headers: dict) -> None:
    r = client.post(
        "/api/v1/prospects",
        json={
            "person_type": "JURIDICA",
            "legal_name": "Empresa SAC",
            "document_number": "12345678901",
            "owner_id": None,
        },
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert "RUC" in r.json()["error"]["message"]


def test_duplicate_document_blocked(client: TestClient, admin_headers: dict) -> None:
    _create_juridica(client, admin_headers, document_number="20131312955")
    r = client.post(
        "/api/v1/prospects",
        json={
            "person_type": "JURIDICA",
            "legal_name": "Otra SAC",
            "document_number": "20131312955",
            "owner_id": None,
        },
        headers=admin_headers,
    )
    assert r.status_code == 409


def test_duplicate_check_endpoint(client: TestClient, admin_headers: dict) -> None:
    _create_juridica(client, admin_headers, document_number="20131312955", email="duplicado@test.pe")
    r = client.post(
        "/api/v1/prospects/duplicate-check",
        json={"email": "duplicado@test.pe"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["matches"]) == 1
    assert body["matches"][0]["field"] == "email"


def test_sales_user_sees_only_own_prospects(
    client: TestClient, admin_headers: dict, sales_headers: dict, sales_user, db: Session
) -> None:
    # Admin crea prospecto asignado a sí mismo
    owned_by_admin = _create_juridica(client, admin_headers, document_number="20131312955")
    # Admin asigna otro prospecto a la vendedora
    r = client.post(
        f"/api/v1/prospects/{owned_by_admin['id']}/assign",
        json={"owner_id": str(sales_user.public_id)},
        headers=admin_headers,
    )
    assert r.status_code == 200

    r = client.get("/api/v1/prospects", headers=sales_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["owner"]["id"] == str(sales_user.public_id)


def test_assign_prospect(client: TestClient, admin_headers: dict, sales_user, db: Session) -> None:
    prospect = _create_natural(client, admin_headers, document_number="12345670")
    r = client.post(
        f"/api/v1/prospects/{prospect['id']}/assign",
        json={"owner_id": str(sales_user.public_id), "reason": "Prueba de asignación"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["owner"]["id"] == str(sales_user.public_id)


def test_change_status(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_natural(client, admin_headers, document_number="12345671")
    r = client.post(
        f"/api/v1/prospects/{prospect['id']}/status",
        json={"status": "EN_PAUSA", "reason": "Fuera de Lima temporalmente"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "EN_PAUSA"


def test_soft_delete_prospect(client: TestClient, admin_headers: dict, db: Session) -> None:
    prospect = _create_natural(client, admin_headers, document_number="12345672")
    r = client.delete(f"/api/v1/prospects/{prospect['id']}", headers=admin_headers)
    assert r.status_code == 204
    p = db.scalar(select(Prospect).where(Prospect.public_id == prospect["id"]))
    assert p is not None
    assert p.deleted_at is not None
