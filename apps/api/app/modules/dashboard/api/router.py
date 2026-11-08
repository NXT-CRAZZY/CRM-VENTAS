from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, require
from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.dashboard.schemas import (
    ConversionSummary,
    ManagementDashboardRead,
    PipelineStageSummary,
    SalesDashboardRead,
    TopPerformer,
    TopProduct,
    UpcomingActionRead,
)
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.products.infrastructure.models import Product
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.quotes.infrastructure.models import Quote, QuoteItem
from app.modules.rbac.domain.permissions import P
from app.modules.tasks.infrastructure.models import Task
from app.modules.users.infrastructure.models import User

router = APIRouter(tags=["Dashboards"], prefix="/dashboard")


def _now_lima() -> datetime:
    # El servidor de base de datos y la app usan America/Lima; se usa UTC para comparaciones.
    return datetime.now(UTC)


def _month_range(now: datetime):
    start_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start_this.month == 1:
        start_last = start_this.replace(year=start_this.year - 1, month=12)
    else:
        start_last = start_this.replace(month=start_this.month - 1)
    return start_this, start_last


def _start_of_day_lima(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("/sales", response_model=SalesDashboardRead)
def sales_dashboard(
    db: DbSession,
    user: Annotated[CurrentUser, Depends(require(P.DASHBOARD_SALES))],
) -> SalesDashboardRead:
    now = _now_lima()
    start_of_day = _start_of_day_lima(now)
    start_of_week = start_of_day - timedelta(days=start_of_day.weekday())

    accessible_filter = True
    if P.PROSPECTS_READ_ALL not in user.permission_codes:
        accessible_filter = Prospect.owner_id == user.id

    # Tareas hoy y vencidas asignadas al usuario
    tasks_today = db.scalar(
        select(func.count(Task.id)).where(
            Task.assignee_id == user.id,
            Task.status == "PENDING",
            Task.due_at >= start_of_day,
            Task.due_at < start_of_day + timedelta(days=1),
            Task.deleted_at.is_(None),
        )
    ) or 0

    tasks_overdue = db.scalar(
        select(func.count(Task.id)).where(
            Task.assignee_id == user.id,
            Task.status == "PENDING",
            Task.due_at < start_of_day,
            Task.deleted_at.is_(None),
        )
    ) or 0

    # Prospectos nuevos asignados esta semana
    new_prospects_this_week = db.scalar(
        select(func.count(Prospect.id)).where(
            Prospect.created_at >= start_of_week,
            Prospect.deleted_at.is_(None),
            accessible_filter,
        )
    ) or 0

    # Seguimientos programados para hoy (próxima acción)
    follow_ups_today = db.scalar(
        select(func.count(Prospect.id)).where(
            Prospect.next_action_at >= start_of_day,
            Prospect.next_action_at < start_of_day + timedelta(days=1),
            Prospect.deleted_at.is_(None),
            accessible_filter,
        )
    ) or 0

    # Sin contacto > 7 días
    seven_days_ago = now - timedelta(days=7)
    prospects_without_contact = db.scalar(
        select(func.count(Prospect.id)).where(
            Prospect.deleted_at.is_(None),
            Prospect.relationship_type == "PROSPECTO",
            accessible_filter,
            (
                (Prospect.last_contact_at.is_(None)) |
                (Prospect.last_contact_at < seven_days_ago)
            ),
        )
    ) or 0

    # Alto interés
    high_interest_id = db.scalar(
        select(CatalogOption.id)
        .join(Catalog, Catalog.id == CatalogOption.catalog_id)
        .where(Catalog.code == "interest_level", CatalogOption.code == "ALTO")
    )
    high_interest_prospects = db.scalar(
        select(func.count(Prospect.id)).where(
            Prospect.interest_level_id == high_interest_id,
            Prospect.deleted_at.is_(None),
            Prospect.relationship_type == "PROSPECTO",
            accessible_filter,
        )
    ) or 0

    # Próximas acciones (tareas + next_action_at de prospectos)
    upcoming_tasks = db.scalars(
        select(Task)
        .where(
            Task.assignee_id == user.id,
            Task.status == "PENDING",
            Task.due_at >= now,
            Task.deleted_at.is_(None),
        )
        .order_by(Task.due_at.asc())
        .limit(5)
    ).all()

    upcoming_prospects = db.scalars(
        select(Prospect)
        .where(
            Prospect.next_action_at >= now,
            Prospect.deleted_at.is_(None),
            accessible_filter,
        )
        .order_by(Prospect.next_action_at.asc())
        .limit(5)
    ).all()

    upcoming_actions: list[UpcomingActionRead] = []
    for t in upcoming_tasks:
        upcoming_actions.append(
            UpcomingActionRead(
                prospect_id=t.prospect.public_id,
                prospect_name=t.prospect.display_name,
                action_type=f"Tarea: {t.title}",
                due_at=t.due_at,
            )
        )
    for p in upcoming_prospects:
        upcoming_actions.append(
            UpcomingActionRead(
                prospect_id=p.public_id,
                prospect_name=p.display_name,
                action_type=p.next_action_desc or "Próxima acción",
                due_at=p.next_action_at,
            )
        )

    upcoming_actions.sort(key=lambda x: (x.due_at or datetime.max.replace(tzinfo=UTC)))
    upcoming_actions = upcoming_actions[:5]

    return SalesDashboardRead(
        tasks_today=tasks_today,
        tasks_overdue=tasks_overdue,
        new_prospects_this_week=new_prospects_this_week,
        follow_ups_today=follow_ups_today,
        prospects_without_contact=prospects_without_contact,
        high_interest_prospects=high_interest_prospects,
        upcoming_actions=upcoming_actions,
    )


@router.get("/management", response_model=ManagementDashboardRead)
def management_dashboard(
    db: DbSession,
    user: Annotated[CurrentUser, Depends(require(P.DASHBOARD_MANAGEMENT))],
) -> ManagementDashboardRead:
    now = _now_lima()
    start_this, start_last = _month_range(now)

    won_stage_id = db.scalar(
        select(CatalogOption.id).join(Catalog).where(
            Catalog.code == "pipeline_stage", CatalogOption.code == "CERRADO_GANADO"
        )
    )

    # Pipeline por etapas
    stage_rows = db.execute(
        select(
            CatalogOption.public_id.label("stage_id"),
            CatalogOption.code,
            CatalogOption.name,
            CatalogOption.color,
            func.count(Opportunity.id).label("opp_count"),
            func.coalesce(func.sum(Opportunity.estimated_amount), 0).label("amount"),
        )
        .join(Opportunity, Opportunity.stage_id == CatalogOption.id)
        .join(Catalog, Catalog.id == CatalogOption.catalog_id)
        .where(
            Catalog.code == "pipeline_stage",
            Opportunity.deleted_at.is_(None),
        )
        .group_by(
            CatalogOption.public_id,
            CatalogOption.code,
            CatalogOption.name,
            CatalogOption.color,
            CatalogOption.sort_order,
        )
        .order_by(CatalogOption.sort_order)
    ).all()

    pipeline = [
        PipelineStageSummary(
            stage_id=row.stage_id,
            stage_code=row.code,
            stage_name=row.name,
            color=row.color,
            count=row.opp_count,
            estimated_amount=float(row.amount),
        )
        for row in stage_rows
    ]

    # Ventas
    sales_this_month = _sales_amount(db, won_stage_id, start_this.date(), now.date())
    sales_last_month = _sales_amount(db, won_stage_id, start_last.date(), start_this.date())

    # Nuevos clientes
    new_clients_this_month = db.scalar(
        select(func.count(Prospect.id)).where(
            Prospect.deleted_at.is_(None),
            Prospect.relationship_type == "CLIENTE",
            Prospect.converted_at >= start_this,
            Prospect.converted_at < now,
        )
    ) or 0

    new_clients_last_month = db.scalar(
        select(func.count(Prospect.id)).where(
            Prospect.deleted_at.is_(None),
            Prospect.relationship_type == "CLIENTE",
            Prospect.converted_at >= start_last,
            Prospect.converted_at < start_this,
        )
    ) or 0

    # Conversión
    total_prospects = db.scalar(select(func.count(Prospect.id)).where(Prospect.deleted_at.is_(None))) or 0
    converted = db.scalar(
        select(func.count(Prospect.id)).where(
            Prospect.deleted_at.is_(None), Prospect.relationship_type == "CLIENTE"
        )
    ) or 0
    conversion_rate = round(converted / total_prospects * 100, 2) if total_prospects else 0.0

    # Top vendedores
    top_rows = db.execute(
        select(
            User.public_id.label("user_id"),
            User.full_name,
            func.count(Opportunity.id).label("won_count"),
            func.coalesce(func.sum(Opportunity.estimated_amount), 0).label("won_amount"),
        )
        .join(Opportunity, Opportunity.owner_id == User.id)
        .where(
            Opportunity.deleted_at.is_(None),
            Opportunity.stage_id == won_stage_id,
            Opportunity.actual_close_date >= start_this.date(),
        )
        .group_by(User.public_id, User.full_name)
        .order_by(func.sum(Opportunity.estimated_amount).desc())
        .limit(5)
    ).all()

    top_performers = [
        TopPerformer(
            user_id=row.user_id,
            full_name=row.full_name,
            won_count=row.won_count,
            won_amount=float(row.won_amount),
        )
        for row in top_rows
    ]

    # Top productos cotizados
    product_rows = db.execute(
        select(
            Product.public_id.label("product_id"),
            Product.name,
            func.count(QuoteItem.id).label("quote_count"),
            func.coalesce(func.sum(QuoteItem.total), 0).label("total_amount"),
        )
        .join(Quote, Quote.id == QuoteItem.quote_id)
        .join(Product, Product.id == QuoteItem.product_id)
        .where(Quote.deleted_at.is_(None))
        .group_by(Product.public_id, Product.name)
        .order_by(func.sum(QuoteItem.total).desc())
        .limit(5)
    ).all()

    top_products = [
        TopProduct(
            product_id=row.product_id,
            product_name=row.name,
            quote_count=row.quote_count,
            total_amount=float(row.total_amount),
        )
        for row in product_rows
    ]

    return ManagementDashboardRead(
        generated_at=now,
        pipeline=pipeline,
        sales_this_month=float(sales_this_month),
        sales_last_month=float(sales_last_month),
        new_clients_this_month=new_clients_this_month,
        new_clients_last_month=new_clients_last_month,
        conversion=ConversionSummary(
            total_prospects=total_prospects,
            converted_to_client=converted,
            conversion_rate=conversion_rate,
        ),
        top_performers=top_performers,
        top_products=top_products,
    )


def _sales_amount(db: Session, stage_id: int | None, start: date, end: date) -> float:
    if stage_id is None:
        return 0.0
    value = db.scalar(
        select(func.coalesce(func.sum(Opportunity.estimated_amount), 0)).where(
            Opportunity.deleted_at.is_(None),
            Opportunity.stage_id == stage_id,
            Opportunity.actual_close_date >= start,
            Opportunity.actual_close_date < end,
        )
    ) or 0
    return float(value)
