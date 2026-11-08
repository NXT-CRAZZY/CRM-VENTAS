from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.infrastructure.models import AuditLog
from app.modules.users.infrastructure.models import User
from tests.conftest import API, PASSWORD, login, make_user


def test_login_returns_token_user_and_httponly_cookie(client: TestClient, sales_user: User) -> None:
    r = client.post(f"{API}/auth/login", json={"email": "VENDEDORA@test.pe", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "vendedora@test.pe"
    assert "prospects.read.own" in body["user"]["permissions"]
    assert "users.manage" not in body["user"]["permissions"]
    cookie = r.headers["set-cookie"]
    assert "crm_refresh=" in cookie and "HttpOnly" in cookie and "samesite=strict" in cookie.lower()
    assert "Path=/api/v1/auth" in cookie


def test_login_wrong_password_is_generic(client: TestClient, sales_user: User) -> None:
    r = client.post(f"{API}/auth/login", json={"email": sales_user.email, "password": "mala"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"
    r2 = client.post(f"{API}/auth/login", json={"email": "noexiste@test.pe", "password": "mala"})
    assert r2.json()["error"]["message"] == r.json()["error"]["message"]


def test_account_locks_after_repeated_failures(client: TestClient, db: Session, sales_user: User) -> None:
    for _ in range(5):
        client.post(f"{API}/auth/login", json={"email": sales_user.email, "password": "mala"})
    r = client.post(f"{API}/auth/login", json={"email": sales_user.email, "password": PASSWORD})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "ACCOUNT_LOCKED"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "auth.locked")) is not None


def test_inactive_user_cannot_login(client: TestClient, db: Session) -> None:
    user = make_user(db, "inactiva@test.pe", "SALES")
    user.is_active = False
    db.flush()
    r = client.post(f"{API}/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "USER_INACTIVE"


def test_me_requires_token(client: TestClient) -> None:
    r = client.get(f"{API}/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_me_with_token(client: TestClient, sales_headers: dict[str, str]) -> None:
    r = client.get(f"{API}/auth/me", headers=sales_headers)
    assert r.status_code == 200
    assert r.json()["roles"][0]["code"] == "SALES"


def test_refresh_rotates_and_detects_reuse(client: TestClient, sales_user: User) -> None:
    client.post(f"{API}/auth/login", json={"email": sales_user.email, "password": PASSWORD})
    first = client.cookies.get("crm_refresh")

    r = client.post(f"{API}/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    second = client.cookies.get("crm_refresh")
    assert second and second != first

    # Reutilizar el token anterior revoca toda la familia...
    client.cookies.set("crm_refresh", first, path="/api/v1/auth")
    r = client.post(f"{API}/auth/refresh")
    assert r.status_code == 401 and r.json()["error"]["code"] == "REFRESH_REUSED"

    # ...incluido el token vigente.
    client.cookies.set("crm_refresh", second, path="/api/v1/auth")
    r = client.post(f"{API}/auth/refresh")
    assert r.status_code == 401


def test_refresh_without_cookie(client: TestClient) -> None:
    r = client.post(f"{API}/auth/refresh")
    assert r.status_code == 401 and r.json()["error"]["code"] == "NO_REFRESH_TOKEN"


def test_logout_revokes_refresh(client: TestClient, sales_user: User) -> None:
    client.post(f"{API}/auth/login", json={"email": sales_user.email, "password": PASSWORD})
    token = client.cookies.get("crm_refresh")
    assert client.post(f"{API}/auth/logout").status_code == 204
    client.cookies.set("crm_refresh", token, path="/api/v1/auth")
    assert client.post(f"{API}/auth/refresh").status_code == 401


def test_change_password(client: TestClient, sales_user: User) -> None:
    headers = login(client, sales_user.email)
    bad = client.post(
        f"{API}/auth/change-password",
        json={"current_password": "incorrecta", "new_password": "Nueva12345"},
        headers=headers,
    )
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "WRONG_PASSWORD"
    weak = client.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "corta"},
        headers=headers,
    )
    assert weak.status_code == 422
    ok = client.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Nueva12345"},
        headers=headers,
    )
    assert ok.status_code == 204
    login(client, sales_user.email, "Nueva12345")
