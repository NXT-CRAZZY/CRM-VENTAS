from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from tests.api.test_interactions import _create_prospect
from tests.conftest import API


def test_sales_dashboard_requires_permission(client: TestClient, sales_headers: dict) -> None:
    r = client.get(f"{API}/dashboard/sales", headers=sales_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "tasks_today" in body
    assert "tasks_overdue" in body


def test_sales_dashboard_counts_tasks(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    due = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
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
