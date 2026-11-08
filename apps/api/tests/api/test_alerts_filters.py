from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.alerts.infrastructure.models import Alert
from app.modules.users.infrastructure.models import User
from tests.conftest import ADMIN_EMAIL, API


def _make_alert(db: Session, user: User, *, status: str, severity: str, title: str) -> Alert:
    alert = Alert(
        user_id=user.id,
        alert_type="NO_FIRST_CONTACT",
        severity=severity,
        status=status,
        title=title,
        message="test",
    )
    db.add(alert)
    db.flush()
    return alert


def _titles(response: dict) -> set[str]:
    return {a["title"] for a in response["items"]}


def test_list_alerts_filters_by_status_and_severity(client: TestClient, admin_headers: dict, db: Session) -> None:
    user = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    assert user is not None

    _make_alert(db, user, status="UNREAD", severity="HIGH", title="unread-high")
    _make_alert(db, user, status="READ", severity="MEDIUM", title="read-medium")
    dismissed = _make_alert(db, user, status="DISMISSED", severity="CRITICAL", title="dismissed-critical")
    dismissed.dismissed_at = datetime.now(UTC)
    db.flush()

    # Sin leer
    r = client.get(f"{API}/alerts", params={"status": "UNREAD"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _titles(r.json()) == {"unread-high"}

    # Leídas
    r = client.get(f"{API}/alerts", params={"status": "READ"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _titles(r.json()) == {"read-medium"}

    # Descartadas
    r = client.get(f"{API}/alerts", params={"status": "DISMISSED"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _titles(r.json()) == {"dismissed-critical"}

    # Todas (sin filtro de status): excluye descartadas
    r = client.get(f"{API}/alerts", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _titles(r.json()) == {"unread-high", "read-medium"}

    # Severidad
    r = client.get(f"{API}/alerts", params={"severity": "HIGH"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _titles(r.json()) == {"unread-high"}

    # Combinación estado + severidad
    r = client.get(f"{API}/alerts", params={"status": "READ", "severity": "MEDIUM"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _titles(r.json()) == {"read-medium"}

    # Combinación que no devuelve nada
    r = client.get(f"{API}/alerts", params={"status": "READ", "severity": "HIGH"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _titles(r.json()) == set()
