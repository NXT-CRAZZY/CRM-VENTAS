from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.infrastructure.models import AuditLog
from app.modules.users.infrastructure.models import User
from tests.conftest import ADMIN_EMAIL, API, PASSWORD, login


def _role_id(client: TestClient, headers: dict[str, str], code: str) -> str:
    roles = client.get(f"{API}/roles", headers=headers).json()
    return next(r["id"] for r in roles if r["code"] == code)


def test_admin_creates_sales_user_who_can_login(client: TestClient, admin_headers: dict[str, str]) -> None:
    payload = {
        "email": "Nueva.Vendedora@dataservice.pe",
        "full_name": "Nueva Vendedora",
        "password": "Temporal123",
        "role_ids": [_role_id(client, admin_headers, "SALES")],
    }
    r = client.post(f"{API}/users", json=payload, headers=admin_headers)
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "nueva.vendedora@dataservice.pe"
    assert r.json()["must_change_password"] is True

    dup = client.post(f"{API}/users", json=payload, headers=admin_headers)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "EMAIL_TAKEN"

    session = client.post(
        f"{API}/auth/login", json={"email": "nueva.vendedora@dataservice.pe", "password": "Temporal123"}
    ).json()
    assert session["user"]["must_change_password"] is True


def test_user_validation_messages_in_spanish(client: TestClient, admin_headers: dict[str, str]) -> None:
    r = client.post(
        f"{API}/users",
        json={"email": "x@y.pe", "full_name": "Ab", "password": "corta", "role_ids": []},
        headers=admin_headers,
    )
    assert r.status_code == 422
    fields = {f["field"]: f["message"] for f in r.json()["error"]["details"]}
    assert "Debe tener al menos 8 caracteres." in fields["password"]
    assert "full_name" in fields and "role_ids" in fields


def test_sales_cannot_manage_users(client: TestClient, sales_headers: dict[str, str]) -> None:
    assert client.get(f"{API}/users", headers=sales_headers).status_code == 403
    r = client.post(f"{API}/roles", json={"name": "Hack"}, headers=sales_headers)
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"


def test_manager_can_manage_users_but_not_roles(client: TestClient, manager_headers: dict[str, str]) -> None:
    assert client.get(f"{API}/users", headers=manager_headers).status_code == 200
    assert client.get(f"{API}/roles", headers=manager_headers).status_code == 200
    assert client.post(f"{API}/roles", json={"name": "Nuevo"}, headers=manager_headers).status_code == 403


def test_user_list_search_and_pagination(client: TestClient, admin_headers: dict[str, str], sales_user: User) -> None:
    r = client.get(f"{API}/users", params={"q": "vendedora", "page_size": 1}, headers=admin_headers)
    body = r.json()
    assert body["total"] == 1 and body["page_size"] == 1
    assert body["items"][0]["email"] == sales_user.email


def test_deactivate_user_revokes_sessions(
    client: TestClient, db: Session, admin_headers: dict[str, str], sales_user: User
) -> None:
    other = TestClient(client.app)
    other.post(f"{API}/auth/login", json={"email": sales_user.email, "password": PASSWORD})

    r = client.post(f"{API}/users/{sales_user.public_id}/deactivate", headers=admin_headers)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert other.post(f"{API}/auth/refresh").status_code == 401

    r = client.post(f"{API}/users/{sales_user.public_id}/activate", headers=admin_headers)
    assert r.json()["is_active"] is True


def test_cannot_deactivate_self_or_last_admin(client: TestClient, db: Session, admin_headers: dict[str, str]) -> None:
    admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    r = client.post(f"{API}/users/{admin.public_id}/deactivate", headers=admin_headers)
    assert r.json()["error"]["code"] == "SELF_DEACTIVATION"

    r = client.patch(
        f"{API}/users/{admin.public_id}",
        json={"role_ids": [_role_id(client, admin_headers, "SALES")]},
        headers=admin_headers,
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "LAST_ADMIN"


def test_role_changes_are_audited(
    client: TestClient, db: Session, admin_headers: dict[str, str], sales_user: User
) -> None:
    client.patch(
        f"{API}/users/{sales_user.public_id}",
        json={"role_ids": [_role_id(client, admin_headers, "MANAGER")]},
        headers=admin_headers,
    )
    log = db.scalar(select(AuditLog).where(AuditLog.action == "user.roles_changed"))
    assert log.before == {"roles": ["SALES"]} and log.after == {"roles": ["MANAGER"]}


def test_permissions_grouped_by_module(client: TestClient, admin_headers: dict[str, str]) -> None:
    groups = client.get(f"{API}/permissions", headers=admin_headers).json()
    modules = {g["module"] for g in groups}
    assert {"Usuarios", "Prospectos", "Productos"} <= modules


def test_custom_role_lifecycle(client: TestClient, db: Session, admin_headers: dict[str, str]) -> None:
    r = client.post(
        f"{API}/roles",
        json={"name": "Supervisora de ventas", "permissions": ["prospects.read.all", "dashboard.sales"]},
        headers=admin_headers,
    )
    assert r.status_code == 201 and r.json()["code"] == "SUPERVISORA_DE_VENTAS"
    role_id = r.json()["id"]

    bad = client.patch(f"{API}/roles/{role_id}", json={"permissions": ["no.existe"]}, headers=admin_headers)
    assert bad.json()["error"]["code"] == "UNKNOWN_PERMISSION"

    client.post(
        f"{API}/users",
        json={"email": "sup@test.pe", "full_name": "Supervisora", "password": "Temporal123", "role_ids": [role_id]},
        headers=admin_headers,
    )
    in_use = client.delete(f"{API}/roles/{role_id}", headers=admin_headers)
    assert in_use.status_code == 409 and in_use.json()["error"]["code"] == "ROLE_IN_USE"


def test_admin_role_permissions_locked_and_system_roles_not_deletable(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    admin_role = _role_id(client, admin_headers, "ADMIN")
    r = client.patch(f"{API}/roles/{admin_role}", json={"permissions": []}, headers=admin_headers)
    assert r.json()["error"]["code"] == "ADMIN_ROLE_LOCKED"
    sales_role = _role_id(client, admin_headers, "SALES")
    assert client.delete(f"{API}/roles/{sales_role}", headers=admin_headers).json()["error"]["code"] == "SYSTEM_ROLE"


def test_sales_permissions_can_be_extended(client: TestClient, admin_headers: dict[str, str], sales_user: User) -> None:
    sales_role = _role_id(client, admin_headers, "SALES")
    roles = client.get(f"{API}/roles", headers=admin_headers).json()
    current = next(r for r in roles if r["code"] == "SALES")["permissions"]
    client.patch(
        f"{API}/roles/{sales_role}", json={"permissions": [*current, "prospects.read.all"]}, headers=admin_headers
    )
    me = client.get(f"{API}/auth/me", headers=login(client, sales_user.email)).json()
    assert "prospects.read.all" in me["permissions"]
