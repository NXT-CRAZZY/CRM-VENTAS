"""Proceso worker de tareas programadas (contenedor `worker`).

Fase 1: limpieza de sesiones expiradas. Desde la fase 7 aquí se registran los jobs de
alertas (seguimientos vencidos, renovaciones, cotizaciones por vencer, estancamiento).

Uso:  python -m app.workers.scheduler
"""

from datetime import UTC, datetime

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

import app.core.models_registry  # noqa: F401
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.modules.alerts.application.use_cases import AlertService
from app.modules.auth.repository import SqlRefreshTokenRepository
from app.modules.scoring.application.use_cases import ScoreCalculator
from app.modules.users.infrastructure.models import User

log = structlog.get_logger()


def purge_expired_sessions() -> int:
    with SessionLocal() as session, session.begin():
        removed = SqlRefreshTokenRepository(session).purge_expired(datetime.now(UTC))
    log.info("job_purge_expired_sessions", removed=removed)
    return removed


def generate_alerts() -> int:
    total = 0
    with SessionLocal() as session, session.begin():
        users = session.scalars(select(User).where(User.is_active.is_(True))).all()  # type: ignore[attr-defined]
        for user in users:
            total += AlertService(session).generate_for_user(user)
    log.info("job_generate_alerts", total=total)
    return total


def recalculate_scores() -> int:
    with SessionLocal() as session, session.begin():
        count = ScoreCalculator(session).recalculate_all()
    log.info("job_recalculate_scores", count=count)
    return count


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=get_settings().timezone)
    scheduler.add_job(purge_expired_sessions, "cron", hour=3, minute=0, id="purge_expired_sessions")
    scheduler.add_job(generate_alerts, "cron", hour=7, minute=0, id="generate_alerts")
    scheduler.add_job(recalculate_scores, "cron", hour=6, minute=0, id="recalculate_scores")
    return scheduler


def main() -> None:
    configure_logging()
    scheduler = build_scheduler()
    log.info("worker_started", jobs=[j.id for j in scheduler.get_jobs()])
    purge_expired_sessions()
    scheduler.start()


if __name__ == "__main__":
    main()
