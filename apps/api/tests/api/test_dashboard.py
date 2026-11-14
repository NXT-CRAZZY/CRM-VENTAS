from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from tests.api.test_interactions import _create_prospect
from app.shared.timeutil import local_day_bounds
from tests.conftest import API


def test_sales_dashboard_requires_permission(client: TestClient, sales_headers: dict) -> None:
    r = client.get(f"{API}/dashboard/sales", headers=sales_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "tasks_today" in body
    assert "tasks_overdue" in body


def test_sales_dashboard_counts_tasks(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    start, end = local_day_bounds()  # "hoy" en hora de Lima, no en UTC
    due = (start + (end - start) / 2).isoformat().replace("+00:00", "Z")
    admin_id = client.get(f"{API}/auth/me", headers=admin_headers).json()["id"]
    r = client.post(
        f"{API}/tasks",
        json={"prospect_id": prospect["id"], "title": "Seguimiento", "due_at": due, "assignee_id": admin_id},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text

    r = client.get(f"{API}/dashboard/sales", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tasks_today"] >= 1


def test_dashboard_counters_match_destination_lists(client: TestClient, admin_headers: dict) -> None:
    """Cada contador del Inicio debe coincidir con el total de la lista a la que enlaza."""
    _create_prospect(client, admin_headers)
    admin_id = client.get(f"{API}/auth/me", headers=admin_headers).json()["id"]
    k = client.get(f"{API}/dashboard/sales", headers=admin_headers).json()

    def total(path: str, **params) -> int:
        r = client.get(f"{API}{path}", headers=admin_headers, params={"page_size": 100, **params})
        assert r.status_code == 200, r.text
        return r.json()["total"]

    assert k["new_prospects_this_week"] == total("/prospects", status="ACTIVO", created_since_days=7)
    assert k["prospects_without_contact"] == total(
        "/prospects", status="ACTIVO", without_contact_days=k["no_contact_days"]
    )
    assert k["high_interest_prospects"] == total(
        "/prospects", status="ACTIVO", interest_level_code="ALTO", relationship_type="PROSPECTO"
    )
    assert k["follow_ups_today"] == total("/prospects", status="ACTIVO", next_action_today="true")
