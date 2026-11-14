from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.api.test_interactions import _create_prospect
from tests.conftest import API


def _product(client: TestClient, headers: dict) -> dict:
    r = client.get(f"{API}/products", headers=headers, params={"page_size": 1})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) > 0, "Se necesita al menos un producto de semilla"
    return items[0]


def test_create_quote_and_list(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    product = _product(client, admin_headers)
    r = client.post(
        f"{API}/quotes",
        json={
            "prospect_id": prospect["id"],
            "issue_date": date.today().isoformat(),
            "expiration_date": (date.today() + timedelta(days=7)).isoformat(),
            "items": [
                {
                    "product_id": product["id"],
                    "description": product["name"],
                    "quantity": 2,
                    "unit_price": float(product["list_price"]),
                }
            ],
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "DRAFT"
    assert len(data["items"]) == 1
    assert float(data["total"]) > 0

    r = client.get(f"{API}/quotes", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1

    r = client.get(f"{API}/quotes", params={"prospect_id": prospect["id"]}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1


def test_accept_quote_converts_prospect(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    product = _product(client, admin_headers)
    r = client.post(
        f"{API}/quotes",
        json={
            "prospect_id": prospect["id"],
            "issue_date": date.today().isoformat(),
            "items": [{"description": product["name"], "quantity": 1, "unit_price": 1000}],
        },
        headers=admin_headers,
    )
    quote_id = r.json()["id"]

    r = client.patch(f"{API}/quotes/{quote_id}/status", json={"status": "SENT"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    r = client.patch(f"{API}/quotes/{quote_id}/status", json={"status": "ACCEPTED"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ACCEPTED"

    r = client.get(f"{API}/prospects/{prospect['id']}", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["relationship_type"] == "CLIENTE"


def _opportunity_for(client: TestClient, headers: dict, prospect_id: str) -> dict:
    from tests.api.test_opportunities import _stage_id, _type_id

    r = client.post(
        f"{API}/opportunities",
        json={
            "prospect_id": prospect_id,
            "title": "Venta para cotizar",
            "stage_id": _stage_id(client, headers, "NUEVO"),
            "type_id": _type_id(client, headers, "NUEVO"),
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _quote_body(client: TestClient, headers: dict, prospect_id: str, **extra) -> dict:
    product = _product(client, headers)
    return {
        "prospect_id": prospect_id,
        "issue_date": date.today().isoformat(),
        "items": [
            {"product_id": product["id"], "description": product["name"], "quantity": 1, "unit_price": 100}
        ],
        **extra,
    }


def test_quote_can_link_to_opportunity_of_same_prospect(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    opp = _opportunity_for(client, admin_headers, prospect["id"])
    r = client.post(
        f"{API}/quotes",
        json=_quote_body(client, admin_headers, prospect["id"], opportunity_id=opp["id"]),
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["opportunity"]["id"] == opp["id"]


def test_quote_rejects_opportunity_of_another_prospect(client: TestClient, admin_headers: dict) -> None:
    a = _create_prospect(client, admin_headers)
    b = _create_prospect(client, admin_headers, document_number="87654321")
    opp_a = _opportunity_for(client, admin_headers, a["id"])
    r = client.post(
        f"{API}/quotes",
        json=_quote_body(client, admin_headers, b["id"], opportunity_id=opp_a["id"]),
        headers=admin_headers,
    )
    assert r.status_code == 404, r.text


# ---------- ciclo de vida ----------


def _set_status(client: TestClient, headers: dict, quote_id: str, status: str, **extra):
    return client.patch(f"{API}/quotes/{quote_id}/status", json={"status": status, **extra}, headers=headers)


def _new_quote(client: TestClient, headers: dict, prospect_id: str, **extra) -> dict:
    r = client.post(f"{API}/quotes", json=_quote_body(client, headers, prospect_id, **extra), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _stage_of(client: TestClient, headers: dict, opp_id: str) -> str:
    r = client.get(f"{API}/opportunities", headers=headers, params={"page_size": 100})
    assert r.status_code == 200, r.text
    return next(o["stage"]["code"] for o in r.json()["items"] if o["id"] == opp_id)


def _loss_reason(client: TestClient, headers: dict) -> str:
    r = client.get(f"{API}/catalogs/bundle", params={"codes": "loss_reason"}, headers=headers)
    return r.json()["catalogs"]["loss_reason"][0]["id"]


def test_quote_invalid_transition(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    q = _new_quote(client, admin_headers, prospect["id"])
    r = _set_status(client, admin_headers, q["id"], "ACCEPTED")  # Borrador -> Aceptada no se permite
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "INVALID_TRANSITION"


def test_send_quote_moves_opportunity_and_freezes(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    opp = _opportunity_for(client, admin_headers, prospect["id"])
    q = _new_quote(client, admin_headers, prospect["id"], opportunity_id=opp["id"])

    r = _set_status(client, admin_headers, q["id"], "SENT")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sent_at"] is not None
    assert data["expiration_date"] is not None  # vigencia por defecto
    assert _stage_of(client, admin_headers, opp["id"]) == "COTIZACION"

    # Enviada = bloqueada
    r = client.patch(f"{API}/quotes/{q['id']}", json={"notes": "x"}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["error"]["code"] == "QUOTE_LOCKED"

    # Reabrir a borrador la desbloquea
    assert _set_status(client, admin_headers, q["id"], "DRAFT").status_code == 200
    r = client.patch(f"{API}/quotes/{q['id']}", json={"notes": "x"}, headers=admin_headers)
    assert r.status_code == 200, r.text


def test_send_quote_links_single_open_opportunity(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    opp = _opportunity_for(client, admin_headers, prospect["id"])
    q = _new_quote(client, admin_headers, prospect["id"])
    r = _set_status(client, admin_headers, q["id"], "SENT")
    assert r.json()["opportunity"]["id"] == opp["id"]


def test_accept_quote_closes_opportunity_won_and_unlocks_on_regress(
    client: TestClient, admin_headers: dict
) -> None:
    from tests.api.test_opportunities import _stage_id

    prospect = _create_prospect(client, admin_headers)
    opp = _opportunity_for(client, admin_headers, prospect["id"])
    q1 = _new_quote(client, admin_headers, prospect["id"], opportunity_id=opp["id"])
    q2 = _new_quote(client, admin_headers, prospect["id"], opportunity_id=opp["id"])
    _set_status(client, admin_headers, q1["id"], "SENT")

    r = _set_status(client, admin_headers, q1["id"], "ACCEPTED")
    assert r.status_code == 200, r.text
    assert _stage_of(client, admin_headers, opp["id"]) == "CERRADO_GANADO"
    # la otra cotización abierta queda descartada
    listing = client.get(f"{API}/quotes", headers=admin_headers, params={"page_size": 100}).json()["items"]
    assert next(x for x in listing if x["id"] == q2["id"])["status"] == "REJECTED"

    # Regresar la oportunidad en el pipeline desbloquea la cotización aceptada
    r = client.patch(
        f"{API}/opportunities/{opp['id']}",
        json={"stage_id": _stage_id(client, admin_headers, "COTIZACION")},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    listing = client.get(f"{API}/quotes", headers=admin_headers, params={"page_size": 100}).json()["items"]
    assert next(x for x in listing if x["id"] == q1["id"])["status"] == "SENT"


def test_reject_quote_requires_reason_and_can_close_opportunity(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    opp = _opportunity_for(client, admin_headers, prospect["id"])
    q = _new_quote(client, admin_headers, prospect["id"], opportunity_id=opp["id"])
    _set_status(client, admin_headers, q["id"], "SENT")

    r = _set_status(client, admin_headers, q["id"], "REJECTED")
    assert r.status_code == 400 and r.json()["error"]["code"] == "REJECT_REASON_REQUIRED"

    reason = _loss_reason(client, admin_headers)
    r = _set_status(client, admin_headers, q["id"], "REJECTED", reject_reason_id=reason)
    assert r.status_code == 200, r.text
    assert r.json()["reject_reason"]["id"] == reason
    assert _stage_of(client, admin_headers, opp["id"]) == "COTIZACION"  # no se cierra sola

    # reabrir y rechazar de nuevo cerrando la oportunidad
    _set_status(client, admin_headers, q["id"], "DRAFT")
    _set_status(client, admin_headers, q["id"], "SENT")
    r = _set_status(client, admin_headers, q["id"], "REJECTED", reject_reason_id=reason, close_opportunity=True)
    assert r.status_code == 200, r.text
    assert _stage_of(client, admin_headers, opp["id"]) == "CERRADO_PERDIDO"


# ---------- filtros y orden ----------


def test_quotes_filters_and_sort(client: TestClient, admin_headers: dict) -> None:
    prospect = _create_prospect(client, admin_headers)
    product = _product(client, admin_headers)
    old = _new_quote(client, admin_headers, prospect["id"], issue_date="2025-01-10")
    new = _new_quote(client, admin_headers, prospect["id"], issue_date="2025-03-10")
    big = client.post(
        f"{API}/quotes",
        json={
            "prospect_id": prospect["id"],
            "issue_date": "2025-02-10",
            "items": [{"description": "Grande", "quantity": 1, "unit_price": 99999}],
        },
        headers=admin_headers,
    ).json()

    def ids(**params) -> list[str]:
        r = client.get(f"{API}/quotes", headers=admin_headers, params={"prospect_id": prospect["id"], **params})
        assert r.status_code == 200, r.text
        return [q["id"] for q in r.json()["items"]]

    assert ids() == [new["id"], big["id"], old["id"]]  # más recientes primero
    assert ids(sort="oldest") == [old["id"], big["id"], new["id"]]
    assert ids(sort="amount_desc")[0] == big["id"]
    assert ids(sort="amount_asc")[-1] == big["id"]
    assert ids(date_from="2025-02-01", date_to="2025-02-28") == [big["id"]]
    assert set(ids(product_id=product["id"])) == {old["id"], new["id"]}
    assert len(ids(search=prospect["display_name"][:5])) == 3
    assert ids(search="zzz-no-existe-zzz") == []
