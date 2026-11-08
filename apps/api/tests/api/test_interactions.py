from datetime import datetime, timezone

from fastapi.testclient import TestClient

from tests.conftest import API


def _catalog_option_id(client: TestClient, headers: dict, catalog_code: str, option_code: str) -> str:
    r = client.get(
        f"{API}/catalogs/bundle",
        params={"codes": f"{catalog_code},contact_mode,contact_result,interest_level"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    option = next(o for o in r.json()["catalogs"][catalog_code] if o["code"] == option_code)
    return option["id"]


def _create_prospect(client: TestClient, headers: dict) -> dict:
    r = client.post(
        f"{API}/prospects",
        json={
            "person_type": "NATURAL",
            "first_name": "Ana",
            "last_name": "López",
            "document_number": "12345673",
            "owner_id": None,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_list_interactions(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    channel_id = _catalog_option_id(client, admin_headers, "contact_channel", "WHATSAPP")
    mode_id = _catalog_option_id(client, admin_headers, "contact_mode", "REMOTO")
    result_id = _catalog_option_id(client, admin_headers, "contact_result", "CONTESTO")
    interest_id = _catalog_option_id(client, admin_headers, "interest_level", "ALTO")

    occurred_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    r = client.post(
        f"{API}/prospects/{prospect['id']}/interactions",
        json={
            "occurred_at": occurred_at,
            "channel_id": channel_id,
            "mode_id": mode_id,
            "result_id": result_id,
            "interest_level_id": interest_id,
            "notes": "Nota de prueba",
            "next_action_desc": "Enviar cotización",
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["attempt_number"] == 1
    assert data["channel"]["id"] == channel_id
    assert data["result"]["id"] == result_id
    assert data["interest_level"]["id"] == interest_id

    r = client.get(f"{API}/prospects/{prospect['id']}/interactions", headers=admin_headers)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["notes"] == "Nota de prueba"


def test_interaction_updates_prospect_summary(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    channel_id = _catalog_option_id(client, admin_headers, "contact_channel", "TELEFONO")
    result_id = _catalog_option_id(client, admin_headers, "contact_result", "SIN_RESPUESTA")

    r = client.post(
        f"{API}/prospects/{prospect['id']}/interactions",
        json={"occurred_at": "2026-10-30T10:00:00Z", "channel_id": channel_id, "result_id": result_id},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text

    r = client.get(f"{API}/prospects/{prospect['id']}", headers=admin_headers)
    assert r.status_code == 200, r.text
    summary = r.json()
    assert summary["interaction_count"] == 1
