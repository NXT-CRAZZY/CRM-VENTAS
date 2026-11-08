from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from tests.api.test_interactions import _create_prospect
from tests.conftest import API


def _type_id(client: TestClient, headers: dict, code: str) -> str:
    r = client.get(f"{API}/catalogs/bundle", params={"codes": "task_type,priority"}, headers=headers)
    assert r.status_code == 200, r.text
    return next(o["id"] for o in r.json()["catalogs"]["task_type"] if o["code"] == code)


def _priority_id(client: TestClient, headers: dict, code: str) -> str:
    r = client.get(f"{API}/catalogs/bundle", params={"codes": "task_type,priority"}, headers=headers)
    assert r.status_code == 200, r.text
    return next(o["id"] for o in r.json()["catalogs"]["priority"] if o["code"] == code)


def test_create_and_list_tasks(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    r = client.post(
        f"{API}/tasks",
        json={
            "prospect_id": prospect["id"],
            "title": "Llamar para seguimiento",
            "description": "Confirmar interés",
            "due_at": due,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Llamar para seguimiento"
    assert data["status"] == "PENDING"

    r = client.get(f"{API}/tasks", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1


def test_complete_task(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    r = client.post(
        f"{API}/tasks",
        json={"prospect_id": prospect["id"], "title": "Enviar correo"},
        headers=admin_headers,
    )
    task_id = r.json()["id"]

    r = client.patch(f"{API}/tasks/{task_id}/status", json={"status": "DONE"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "DONE"
    assert r.json()["completed_at"] is not None


def test_delete_task(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    r = client.post(
        f"{API}/tasks",
        json={"prospect_id": prospect["id"], "title": "Tarea a eliminar"},
        headers=admin_headers,
    )
    task_id = r.json()["id"]

    r = client.delete(f"{API}/tasks/{task_id}", headers=admin_headers)
    assert r.status_code == 204, r.text

    r = client.get(f"{API}/tasks", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 0
