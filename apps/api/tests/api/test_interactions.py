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


def _create_prospect(client: TestClient, headers: dict, document_number: str = "12345673") -> dict:
    r = client.post(
        f"{API}/prospects",
        json={
            "person_type": "NATURAL",
            "first_name": "Ana",
            "last_name": "López",
            "document_number": document_number,
            "owner_id": None,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_list_interactions(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    channel_id = _catalog_option_id(client, admin_headers, "contact_channel", "WHATSAPP")
    result_id = _catalog_option_id(client, admin_headers, "contact_result", "CONTESTO")
    interest_id = _catalog_option_id(client, admin_headers, "interest_level", "ALTO")

    occurred_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    r = client.post(
        f"{API}/prospects/{prospect['id']}/interactions",
        json={
            "occurred_at": occurred_at,
            "channel_id": channel_id,
            "result_id": result_id,
            "interest_level_id": interest_id,
            "notes": "Nota de prueba",
            "follow_up_task": {
                "title": "Enviar cotización",
                "description": "Con precios actualizados",
                "due_at": "2030-01-15T15:00:00Z",
            },
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["attempt_number"] == 1
    assert data["channel"]["id"] == channel_id
    assert data["mode"]["code"] == "REMOTO"
    assert data["result"]["id"] == result_id
    assert data["interest_level"]["id"] == interest_id
    assert data["follow_up_task"]["title"] == "Enviar cotización"
    assert data["follow_up_task"]["status"] == "PENDING"

    r = client.get(f"{API}/prospects/{prospect['id']}/interactions", headers=admin_headers)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["notes"] == "Nota de prueba"

    # La próxima acción se convierte en una tarea pendiente del prospecto.
    r = client.get(f"{API}/tasks", headers=admin_headers)
    assert r.status_code == 200, r.text
    tasks = [t for t in r.json()["items"] if t["title"] == "Enviar cotización"]
    assert len(tasks) == 1
    assert tasks[0]["status"] == "PENDING"


def test_interaction_without_next_action_creates_no_task(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    channel_id = _catalog_option_id(client, admin_headers, "contact_channel", "TELEFONO")
    result_id = _catalog_option_id(client, admin_headers, "contact_result", "SIN_RESPUESTA")

    r = client.post(
        f"{API}/prospects/{prospect['id']}/interactions",
        json={"occurred_at": "2026-10-30T10:00:00Z", "channel_id": channel_id, "result_id": result_id},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text

    r = client.get(f"{API}/tasks", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["items"] == []


def test_visita_presencial_infers_presencial_mode(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    channel_id = _catalog_option_id(client, admin_headers, "contact_channel", "VISITA")
    result_id = _catalog_option_id(client, admin_headers, "contact_result", "CONTESTO")

    r = client.post(
        f"{API}/prospects/{prospect['id']}/interactions",
        json={"occurred_at": "2026-10-30T10:00:00Z", "channel_id": channel_id, "result_id": result_id},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["mode"]["code"] == "PRESENCIAL"


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


def _new_interaction(client: TestClient, headers: dict, prospect: dict, **extra) -> dict:
    channel_id = _catalog_option_id(client, headers, "contact_channel", "TELEFONO")
    result_id = _catalog_option_id(client, headers, "contact_result", "CONTESTO")
    r = client.post(
        f"{API}/prospects/{prospect['id']}/interactions",
        json={"occurred_at": "2026-10-30T10:00:00Z", "channel_id": channel_id, "result_id": result_id, **extra},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _tasks(client: TestClient, headers: dict, prospect: dict) -> list[dict]:
    r = client.get(f"{API}/tasks", params={"prospect_id": prospect["id"]}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["items"]


def test_edit_interaction_adds_updates_and_removes_follow_up(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    interaction = _new_interaction(client, admin_headers, prospect)
    assert interaction["follow_up_task"] is None
    url = f"{API}/prospects/{prospect['id']}/interactions/{interaction['id']}"

    # Añadir desde la edición
    r = client.patch(url, json={"follow_up_task": {"title": "Llamar", "due_at": "2030-02-01T15:00:00Z"}}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["follow_up_task"]["title"] == "Llamar"
    assert len(_tasks(client, admin_headers, prospect)) == 1

    # Editar la tarea vinculada (no duplica)
    r = client.patch(url, json={"follow_up_task": {"title": "Llamar de nuevo", "due_at": "2030-02-02T15:00:00Z"}}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["follow_up_task"]["title"] == "Llamar de nuevo"
    assert len(_tasks(client, admin_headers, prospect)) == 1

    # Quitar
    r = client.patch(url, json={"remove_follow_up_task": True}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["follow_up_task"] is None
    assert _tasks(client, admin_headers, prospect) == []


def test_delete_interaction_removes_pending_follow_up_only(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    pending = _new_interaction(
        client, admin_headers, prospect,
        follow_up_task={"title": "Pendiente", "due_at": "2030-01-15T15:00:00Z"},
    )
    done = _new_interaction(
        client, admin_headers, prospect,
        follow_up_task={"title": "Completada", "due_at": "2030-01-16T15:00:00Z"},
    )
    done_task_id = done["follow_up_task"]["id"]
    r = client.patch(f"{API}/tasks/{done_task_id}/status", json={"status": "DONE"}, headers=admin_headers)
    assert r.status_code == 200, r.text

    for i in (pending, done):
        r = client.delete(f"{API}/prospects/{prospect['id']}/interactions/{i['id']}", headers=admin_headers)
        assert r.status_code == 204, r.text

    titles = [t["title"] for t in _tasks(client, admin_headers, prospect)]
    assert titles == ["Completada"]


def _interact(client: TestClient, headers: dict, prospect_id: str, result_code: str) -> dict:
    channel_id = _catalog_option_id(client, headers, "contact_channel", "WHATSAPP")
    result_id = _catalog_option_id(client, headers, "contact_result", result_code)
    r = client.post(
        f"{API}/prospects/{prospect_id}/interactions",
        json={
            "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "channel_id": channel_id,
            "result_id": result_id,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _opportunities(client: TestClient, headers: dict, prospect_id: str) -> list[dict]:
    r = client.get(f"{API}/opportunities", params={"prospect_id": prospect_id}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["items"]


def test_result_without_pipeline_effect_creates_nothing(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    for code in ("VOLVER_LLAMAR", "SIN_RESPUESTA"):
        data = _interact(client, admin_headers, prospect["id"], code)
        assert data["opportunity"] is None
        assert data["opportunity_action"] is None
    assert _opportunities(client, admin_headers, prospect["id"]) == []


def test_result_creates_then_advances_single_opportunity(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)

    data = _interact(client, admin_headers, prospect["id"], "CONTESTO")
    assert data["opportunity_action"] == "created"
    assert data["opportunity"]["stage"]["code"] == "NUEVO"

    data = _interact(client, admin_headers, prospect["id"], "DEMOSTRACION")
    assert data["opportunity_action"] == "moved"
    assert data["opportunity"]["stage"]["code"] == "DEMOSTRACION"

    data = _interact(client, admin_headers, prospect["id"], "COTIZACION")
    assert data["opportunity"]["stage"]["code"] == "COTIZACION"

    # No retrocede: un "Contestó" posterior no baja la oportunidad de Cotización
    data = _interact(client, admin_headers, prospect["id"], "CONTESTO")
    assert data["opportunity_action"] is None
    items = _opportunities(client, admin_headers, prospect["id"])
    assert len(items) == 1
    assert items[0]["stage"]["code"] == "COTIZACION"


def test_venta_closes_won_and_no_interesado_closes_lost(client: TestClient, admin_headers: dict) -> None:
    won = _create_prospect(client, admin_headers)
    _interact(client, admin_headers, won["id"], "COTIZACION")
    data = _interact(client, admin_headers, won["id"], "VENTA")
    assert data["opportunity_action"] == "closed"
    opp = _opportunities(client, admin_headers, won["id"])[0]
    assert opp["stage"]["code"] == "CERRADO_GANADO"
    assert opp["actual_close_date"] is not None

    lost = _create_prospect(client, admin_headers, "87654321")
    _interact(client, admin_headers, lost["id"], "DEMOSTRACION")
    data = _interact(client, admin_headers, lost["id"], "NO_INTERESADO")
    assert data["opportunity_action"] == "closed"
    opp = _opportunities(client, admin_headers, lost["id"])[0]
    assert opp["stage"]["code"] == "CERRADO_PERDIDO"


def test_no_interesado_without_open_opportunity_registers_lost(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    data = _interact(client, admin_headers, prospect["id"], "NO_INTERESADO")
    assert data["opportunity_action"] == "created"
    assert data["opportunity"]["stage"]["code"] == "CERRADO_PERDIDO"

    # Repetirlo no duplica la oportunidad perdida
    data = _interact(client, admin_headers, prospect["id"], "NO_INTERESADO")
    assert data["opportunity_action"] is None
    assert len(_opportunities(client, admin_headers, prospect["id"])) == 1


def test_no_interesado_after_won_keeps_won_and_adds_lost(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    _interact(client, admin_headers, prospect["id"], "VENTA")
    data = _interact(client, admin_headers, prospect["id"], "NO_INTERESADO")
    assert data["opportunity_action"] == "created"
    stages = sorted(o["stage"]["code"] for o in _opportunities(client, admin_headers, prospect["id"]))
    assert stages == ["CERRADO_GANADO", "CERRADO_PERDIDO"]


def _interact_with(client: TestClient, headers: dict, prospect_id: str, result_code: str, **extra):
    channel_id = _catalog_option_id(client, headers, "contact_channel", "WHATSAPP")
    result_id = _catalog_option_id(client, headers, "contact_result", result_code)
    return client.post(
        f"{API}/prospects/{prospect_id}/interactions",
        json={
            "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "channel_id": channel_id,
            "result_id": result_id,
            **extra,
        },
        headers=headers,
    )


def test_new_opportunity_from_interaction_uses_given_title_and_type(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    type_id = _catalog_option_id(client, admin_headers, "opportunity_type", "USUARIOS_ADICIONALES")
    r = _interact_with(
        client, admin_headers, prospect["id"], "COTIZACION",
        new_opportunity={"title": "Empresarial 2 terminales + usuario", "type_id": type_id},
    )
    assert r.status_code == 201, r.text
    opp = r.json()["opportunity"]
    assert opp["title"] == "Empresarial 2 terminales + usuario"
    assert r.json()["opportunity_action"] == "created"
    [saved] = _opportunities(client, admin_headers, prospect["id"])
    assert saved["type"]["code"] == "USUARIOS_ADICIONALES"
    assert saved["stage"]["code"] == "COTIZACION"


def test_new_opportunity_is_created_even_if_one_is_open(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    _interact(client, admin_headers, prospect["id"], "CONTESTO")
    type_id = _catalog_option_id(client, admin_headers, "opportunity_type", "CAMBIO_PLAN")
    r = _interact_with(
        client, admin_headers, prospect["id"], "COTIZACION",
        new_opportunity={"title": "Cambio a Profesional", "type_id": type_id},
    )
    assert r.status_code == 201, r.text
    assert len(_opportunities(client, admin_headers, prospect["id"])) == 2


def test_several_open_opportunities_require_a_choice(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    _interact(client, admin_headers, prospect["id"], "CONTESTO")
    type_id = _catalog_option_id(client, admin_headers, "opportunity_type", "CAMBIO_PLAN")
    _interact_with(
        client, admin_headers, prospect["id"], "CONTESTO",
        new_opportunity={"title": "Segundo negocio", "type_id": type_id},
    )
    r = _interact_with(client, admin_headers, prospect["id"], "COTIZACION")
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "OPPORTUNITY_REQUIRED"

    opps = _opportunities(client, admin_headers, prospect["id"])
    target = next(o for o in opps if o["title"] == "Segundo negocio")
    other = next(o for o in opps if o["title"] != "Segundo negocio")
    r = _interact_with(client, admin_headers, prospect["id"], "COTIZACION", opportunity_id=target["id"])
    assert r.status_code == 201, r.text
    assert r.json()["opportunity"]["id"] == target["id"]
    after = {o["id"]: o["stage"]["code"] for o in _opportunities(client, admin_headers, prospect["id"])}
    assert after[target["id"]] == "COTIZACION"
    assert after[other["id"]] == "NUEVO"


def test_cannot_pick_opportunity_of_another_prospect_or_closed(client: TestClient, admin_headers: dict) -> None:
    a = _create_prospect(client, admin_headers)
    b = _create_prospect(client, admin_headers, document_number="87654321")
    _interact(client, admin_headers, a["id"], "CONTESTO")
    foreign = _opportunities(client, admin_headers, a["id"])[0]
    r = _interact_with(client, admin_headers, b["id"], "COTIZACION", opportunity_id=foreign["id"])
    assert r.status_code == 404, r.text

    _interact(client, admin_headers, a["id"], "VENTA")
    r = _interact_with(client, admin_headers, a["id"], "COTIZACION", opportunity_id=foreign["id"])
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "OPPORTUNITY_CLOSED"
