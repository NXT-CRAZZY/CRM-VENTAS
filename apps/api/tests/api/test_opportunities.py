from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.prospects.infrastructure.models import Prospect

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
            "type_id": _type_id(client, admin_headers, "NUEVO"),
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

    r = client.get(f"{API}/opportunities", params={"prospect_id": prospect["id"]}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1


def test_update_opportunity_stage(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    stage_new = _stage_id(client, admin_headers, "NUEVO")
    stage_quote = _stage_id(client, admin_headers, "COTIZACION")
    r = client.post(
        f"{API}/opportunities",
        json={"prospect_id": prospect["id"], "title": "Renovación anual", "stage_id": stage_new, "type_id": _type_id(client, admin_headers, "NUEVO")},
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
        json={"prospect_id": prospect["id"], "title": "Oportunidad a eliminar", "stage_id": stage, "type_id": _type_id(client, admin_headers, "NUEVO")},
        headers=admin_headers,
    )
    opp_id = r.json()["id"]

    r = client.delete(f"{API}/opportunities/{opp_id}", headers=admin_headers)
    assert r.status_code == 204, r.text

    r = client.get(f"{API}/opportunities", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 0


def test_loss_reason_cleared_when_leaving_lost_stage(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    lost = _stage_id(client, admin_headers, "CERRADO_PERDIDO")
    new = _stage_id(client, admin_headers, "NUEVO")
    r = client.get(f"{API}/catalogs/bundle", params={"codes": "loss_reason"}, headers=admin_headers)
    reason = r.json()["catalogs"]["loss_reason"][0]["id"]

    r = client.post(
        f"{API}/opportunities",
        json={"prospect_id": prospect["id"], "title": "Perdida", "stage_id": lost, "loss_reason_id": reason, "type_id": _type_id(client, admin_headers, "NUEVO")},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["loss_reason"]["id"] == reason

    r = client.patch(f"{API}/opportunities/{r.json()['id']}", json={"stage_id": new}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["loss_reason"] is None


def test_client_status_is_frozen_at_creation(client: TestClient, admin_headers: dict, db: Session) -> None:
    prospect = _create_prospect(client, admin_headers)
    stage = _stage_id(client, admin_headers, "NUEVO")
    r = client.post(
        f"{API}/opportunities",
        json={"prospect_id": prospect["id"], "title": "Primera compra", "stage_id": stage, "type_id": _type_id(client, admin_headers, "NUEVO")},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    first = r.json()
    assert first["client_status"] == "NUEVO"

    p = db.scalar(select(Prospect).where(Prospect.public_id == prospect["id"]))
    assert p is not None
    p.relationship_type = "CLIENTE"
    db.add(p)
    db.commit()

    r = client.post(
        f"{API}/opportunities",
        json={"prospect_id": prospect["id"], "title": "Más usuarios", "stage_id": stage, "type_id": _type_id(client, admin_headers, "USUARIOS_ADICIONALES")},
        headers=admin_headers,
    )
    assert r.json()["client_status"] == "EXISTENTE"
    r = client.get(f"{API}/opportunities", params={"prospect_id": prospect["id"]}, headers=admin_headers)
    by_title = {o["title"]: o["client_status"] for o in r.json()["items"]}
    assert by_title == {"Primera compra": "NUEVO", "Más usuarios": "EXISTENTE"}


def test_type_is_required_when_creating(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    r = client.post(
        f"{API}/opportunities",
        json={"prospect_id": prospect["id"], "title": "Sin tipo", "stage_id": _stage_id(client, admin_headers, "NUEVO")},
        headers=admin_headers,
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "TYPE_REQUIRED"


def test_type_is_optional_for_cerrado_perdido(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    r = client.post(
        f"{API}/opportunities",
        json={"prospect_id": prospect["id"], "title": "Perdida sin tipo", "stage_id": _stage_id(client, admin_headers, "CERRADO_PERDIDO")},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["type"] is None


def test_created_opportunity_defaults_owner_and_is_visible_to_creator(client: TestClient, sales_headers: dict) -> None:
    prospect = _create_prospect(client, sales_headers)
    r = client.post(
        f"{API}/opportunities",
        json={
            "prospect_id": prospect["id"],
            "title": "Perdida directa",
            "stage_id": _stage_id(client, sales_headers, "CERRADO_PERDIDO"),
        },
        headers=sales_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["owner"] is not None
    r = client.get(f"{API}/opportunities", headers=sales_headers)
    assert [o["title"] for o in r.json()["items"]] == ["Perdida directa"]
