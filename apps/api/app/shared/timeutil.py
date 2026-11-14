"""Limites de "hoy" en la zona horaria del negocio (America/Lima), no en UTC."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def local_day_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Inicio y fin (exclusivo) del dia local, expresados en UTC."""
    tz = ZoneInfo(get_settings().timezone)
    local_now = (now or datetime.now(UTC)).astimezone(tz)
    start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)
