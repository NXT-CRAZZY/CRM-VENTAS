from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.prospects.infrastructure.models import Prospect
from tests.api.test_interactions import _catalog_option_id, _create_prospect
from tests.conftest import API


def test_recalculate_prospect_score(client: TestClient, admin_headers: dict) -> None:
    interest_id = _catalog_option_id(client, admin_headers, "interest_level", "ALTO")
    priority_id = _catalog_option_id(client, admin_headers, "priority", "ALTA")
    prospect = _create_prospect(client, admin_headers)

    r = client.patch(
        f"{API}/prospects/{prospect['id']}",
        json={"interest_level_id": interest_id, "priority_id": priority_id},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text

    r = client.post(f"{API}/scoring/prospects/{prospect['id']}/recalculate", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["score"]) > 0
    assert "interest_level" in body["breakdown"]
    assert "priority" in body["breakdown"]


def test_recalculate_all_requires_permission(client: TestClient, sales_headers: dict) -> None:
    r = client.post(f"{API}/scoring/recalculate-all", headers=sales_headers)
    assert r.status_code == 403, r.text


def test_recalculate_all_as_manager(client: TestClient, manager_headers: dict, db: Session) -> None:
    r = client.post(f"{API}/scoring/recalculate-all", headers=manager_headers)
    assert r.status_code == 200, r.text
    assert r.json() >= 0


def test_score_increases_when_converted_to_client(client: TestClient, admin_headers: dict, db: Session) -> None:
    prospect = _create_prospect(client, admin_headers)
    r = client.post(f"{API}/scoring/prospects/{prospect['id']}/recalculate", headers=admin_headers)
    before = float(r.json()["score"])

    p = db.scalar(select(Prospect).where(Prospect.public_id == prospect["id"]))
    assert p is not None
    p.relationship_type = "CLIENTE"
    db.add(p)
    db.commit()

    r = client.post(f"{API}/scoring/prospects/{prospect['id']}/recalculate", headers=admin_headers)
    after = float(r.json()["score"])
    assert after > before
    assert r.json()["breakdown"]["client"] == 25
