"""Cálculo del informe de ventas (pantalla y Excel comparten estos números).

Reglas:
- Cotizaciones: cotizaciones ya enviadas (no borradores), contadas por su fecha de envío.
- Ventas: TODAS las oportunidades en Cerrado ganado, con o sin cotización, por fecha de cierre y
  con su monto. Se desglosan por tipo y lo que no tiene tipo va en "Sin definir".
- Nuevos clientes: prospectos que pasaron a cliente (fecha de conversión).
- Alcance: el vendedor ve solo lo suyo; quien tiene "ver todos los prospectos" (administrador y
  gerente) ve todo y puede filtrar por vendedor.
- Los días se miden en la zona horaria del negocio (Lima), no en UTC.
- Filtros: rango de fechas libre, vendedor, producto y tipo de venta. Producto y tipo no aplican a
  "Nuevos clientes".
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.imports.schemas import (
    WeeklyDetailItem,
    WeeklyReport,
    WeeklyReportFilters,
    WeeklyReportRow,
)
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.products.infrastructure.models import Product
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.quotes.infrastructure.models import Quote, QuoteItem
from app.modules.rbac.domain.permissions import P
from app.modules.users.infrastructure.models import User

PERIODS = ("today", "week", "month", "range")


class Period:
    """Rango [start, end) como fechas y como instantes aware (hora local)."""

    def __init__(self, start: date, end: date, tz: ZoneInfo) -> None:
        self.start, self.end = start, end
        self.start_dt = datetime.combine(start, time.min, tzinfo=tz)
        self.end_dt = datetime.combine(end, time.min, tzinfo=tz)


@dataclass
class _Ctx:
    s: Session
    user: User
    see_all: bool
    seller_id: int | None
    product_id: int | None
    type_id: int | None
    periods: dict[str, Period]


def local_today() -> date:
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


def _parse(value: str | None) -> date | None:
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def _context(s: Session, user: User, f: WeeklyReportFilters) -> _Ctx:
    tz = ZoneInfo(get_settings().timezone)
    target = _parse(f.date) or local_today()
    next_day = target + timedelta(days=1)
    periods = {
        "today": Period(target, next_day, tz),
        "week": Period(target - timedelta(days=target.weekday()), next_day, tz),
        "month": Period(target.replace(day=1), next_day, tz),
    }
    d_from, d_to = _parse(f.date_from), _parse(f.date_to)
    if d_from or d_to:
        d_from = d_from or d_to
        d_to = d_to or d_from
        if d_to < d_from:
            raise AppError("La fecha final no puede ser anterior a la inicial.", code="INVALID_RANGE")
        periods["range"] = Period(d_from, d_to + timedelta(days=1), tz)

    see_all = P.PROSPECTS_READ_ALL in user.permission_codes
    seller_id = None
    if f.seller_id and see_all:
        seller_id = s.scalar(select(User.id).where(User.public_id == UUID(f.seller_id))) or -1
    product_id = None
    if f.product_id:
        product_id = s.scalar(select(Product.id).where(Product.public_id == UUID(f.product_id))) or -1
    type_id = None
    if f.type_id:
        type_id = s.scalar(select(CatalogOption.id).where(CatalogOption.public_id == UUID(f.type_id))) or -1
    return _Ctx(s, user, see_all, seller_id, product_id, type_id, periods)


# ---------- consultas base (reutilizadas por los totales y por el detalle) ----------


def _owner(c: _Ctx) -> int | None:
    """Dueño al que se limita el informe: el propio vendedor, o el vendedor elegido por la gerencia."""
    if not c.see_all:
        return c.user.id
    return c.seller_id


def _quote_filter(c: _Ctx, p: Period):
    conds = [
        Quote.deleted_at.is_(None),
        Quote.status != "DRAFT",
        Quote.sent_at >= p.start_dt,
        Quote.sent_at < p.end_dt,
    ]
    owner = _owner(c)
    if owner is not None:
        conds.append(Quote.prospect_id.in_(select(Prospect.id).where(Prospect.owner_id == owner)))
    if c.product_id is not None:
        conds.append(Quote.id.in_(select(QuoteItem.quote_id).where(QuoteItem.product_id == c.product_id)))
    if c.type_id is not None:
        conds.append(Quote.opportunity_id.in_(select(Opportunity.id).where(Opportunity.type_id == c.type_id)))
    return conds


def _sale_filter(c: _Ctx, p: Period, won_id: int | None):
    conds = [
        Opportunity.deleted_at.is_(None),
        Opportunity.stage_id == (won_id if won_id is not None else -1),
        Opportunity.actual_close_date >= p.start,
        Opportunity.actual_close_date < p.end,
    ]
    owner = _owner(c)
    if owner is not None:
        conds.append(
            or_(
                Opportunity.owner_id == owner,
                Opportunity.prospect_id.in_(select(Prospect.id).where(Prospect.owner_id == owner)),
            )
        )
    if c.type_id is not None:
        conds.append(Opportunity.type_id == c.type_id)
    if c.product_id is not None:
        conds.append(
            Opportunity.id.in_(
                select(Quote.opportunity_id)
                .join(QuoteItem, QuoteItem.quote_id == Quote.id)
                .where(
                    Quote.status == "ACCEPTED",
                    Quote.deleted_at.is_(None),
                    Quote.opportunity_id.is_not(None),
                    QuoteItem.product_id == c.product_id,
                )
            )
        )
    return conds


def _client_filter(c: _Ctx, p: Period):
    conds = [
        Prospect.deleted_at.is_(None),
        Prospect.relationship_type == "CLIENTE",
        Prospect.converted_at >= p.start_dt,
        Prospect.converted_at < p.end_dt,
    ]
    owner = _owner(c)
    if owner is not None:
        conds.append(Prospect.owner_id == owner)
    return conds


def _won_id(s: Session) -> int | None:
    return s.scalar(
        select(CatalogOption.id)
        .join(Catalog, Catalog.id == CatalogOption.catalog_id)
        .where(Catalog.code == "pipeline_stage", CatalogOption.code == "CERRADO_GANADO")
    )


# ---------- informe ----------


def build_weekly_report(s: Session, user: User, filters: WeeklyReportFilters | None = None) -> WeeklyReport:
    f = filters or WeeklyReportFilters()
    c = _context(s, user, f)
    won_id = _won_id(s)
    types = list(
        s.execute(
            select(CatalogOption.id, CatalogOption.code, CatalogOption.name, CatalogOption.public_id)
            .join(Catalog, Catalog.id == CatalogOption.catalog_id)
            .where(Catalog.code == "opportunity_type")
            .order_by(CatalogOption.sort_order, CatalogOption.id)
        ).all()
    )

    def quotes(p: Period) -> tuple[int, float]:
        n, total = s.execute(
            select(func.count(Quote.id), func.coalesce(func.sum(Quote.total), 0)).where(*_quote_filter(c, p))
        ).one()
        return int(n), float(total)

    def sales(p: Period) -> tuple[int, float, dict[int | None, float]]:
        by_type: dict[int | None, float] = {}
        count = 0
        stmt = (
            select(Opportunity.type_id, func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.estimated_amount), 0))
            .where(*_sale_filter(c, p, won_id))
            .group_by(Opportunity.type_id)
        )
        for type_id, n, total in s.execute(stmt).all():
            by_type[type_id] = float(total)
            count += int(n)
        return count, sum(by_type.values()), by_type

    def clients(p: Period) -> int:
        return int(s.scalar(select(func.count(Prospect.id)).where(*_client_filter(c, p))) or 0)

    q = {k: quotes(p) for k, p in c.periods.items()}
    v = {k: sales(p) for k, p in c.periods.items()}
    cl = {k: clients(p) for k, p in c.periods.items()}
    keys = [k for k in PERIODS if k in c.periods]

    def row(label: str, key: str, kind: str, getter) -> WeeklyReportRow:
        vals = {k: getter(k) for k in keys}
        return WeeklyReportRow(
            label=label,
            key=key,
            kind=kind,
            today=vals["today"],
            week=vals["week"],
            month=vals["month"],
            range=vals.get("range"),
        )

    rows = [
        row("Cotizaciones enviadas", "quotes", "count", lambda k: q[k][0]),
        row("Monto cotizado", "quotes", "money", lambda k: q[k][1]),
        row("Ventas cerradas (cantidad)", "sales", "count", lambda k: v[k][0]),
        row("Ventas totales", "sales", "money", lambda k: v[k][1]),
    ]
    for type_id, _code, name, public_id in types:
        rows.append(row(f"   {name}", f"sales:{public_id}", "money", lambda k, t=type_id: v[k][2].get(t, 0.0)))
    rows.append(row("   Sin definir", "sales:none", "money", lambda k: v[k][2].get(None, 0.0)))
    rows.append(row("Nuevos clientes", "clients", "count", lambda k: cl[k]))

    def by_code(code: str, k: str) -> float:
        tid = next((t[0] for t in types if t[1] == code), None)
        return v[k][2].get(tid, 0.0) if tid is not None else 0.0

    r = c.periods.get("range")
    return WeeklyReport(
        generated_at=datetime.now(UTC),
        quotes_today=q["today"][0],
        quotes_month=q["month"][0],
        sales_today=v["today"][1],
        sales_month=v["month"][1],
        sales_update_today=by_code("ACTUALIZACION", "today"),
        sales_update_month=by_code("ACTUALIZACION", "month"),
        sales_new_today=by_code("NUEVO", "today"),
        sales_new_month=by_code("NUEVO", "month"),
        new_clients_today=cl["today"],
        new_clients_month=cl["month"],
        range_label=(
            f"{r.start.strftime('%d/%m/%Y')} al {(r.end - timedelta(days=1)).strftime('%d/%m/%Y')}" if r else None
        ),
        rows=rows,
    )


# ---------- detalle: lista de lo que compone cada número ----------


def build_weekly_detail(
    s: Session, user: User, filters: WeeklyReportFilters, key: str, period: str
) -> list[WeeklyDetailItem]:
    c = _context(s, user, filters)
    if period not in c.periods:
        raise AppError("Periodo no válido.", code="INVALID_PERIOD")
    p = c.periods[period]
    items: list[WeeklyDetailItem] = []

    if key == "quotes":
        stmt = select(Quote).where(*_quote_filter(c, p)).order_by(Quote.sent_at.desc()).limit(200)
        for q in s.scalars(stmt).unique().all():
            items.append(
                WeeklyDetailItem(
                    id=q.public_id,
                    prospect_id=q.prospect.public_id,
                    prospect_name=q.prospect.display_name,
                    day=q.sent_at.astimezone(ZoneInfo(get_settings().timezone)).date() if q.sent_at else None,
                    amount=float(q.total),
                    description=", ".join(i.description for i in q.items) or None,
                    status=q.status,
                    seller=q.prospect.owner.full_name if q.prospect.owner else None,
                )
            )
    elif key.startswith("sales"):
        conds = _sale_filter(c, p, _won_id(s))
        if key.startswith("sales:"):
            _, _, ref = key.partition(":")
            if ref == "none":
                conds.append(Opportunity.type_id.is_(None))
            else:
                conds.append(
                    Opportunity.type_id == (s.scalar(select(CatalogOption.id).where(CatalogOption.public_id == UUID(ref))) or -1)
                )
        stmt = select(Opportunity).where(*conds).order_by(Opportunity.actual_close_date.desc()).limit(200)
        for o in s.scalars(stmt).unique().all():
            accepted = s.scalar(
                select(Quote).where(Quote.opportunity_id == o.id, Quote.status == "ACCEPTED", Quote.deleted_at.is_(None))
            )
            desc = ", ".join(i.description for i in accepted.items) if accepted and accepted.items else o.title
            items.append(
                WeeklyDetailItem(
                    id=o.public_id,
                    prospect_id=o.prospect.public_id,
                    prospect_name=o.prospect.display_name,
                    day=o.actual_close_date,
                    amount=float(o.estimated_amount) if o.estimated_amount is not None else None,
                    description=desc,
                    status=(o.type.name if o.type else "Sin definir") + (" · con cotización" if accepted else " · sin cotización"),
                    seller=o.owner.full_name if o.owner else None,
                )
            )
    elif key == "clients":
        stmt = select(Prospect).where(*_client_filter(c, p)).order_by(Prospect.converted_at.desc()).limit(200)
        for pr in s.scalars(stmt).unique().all():
            items.append(
                WeeklyDetailItem(
                    id=pr.public_id,
                    prospect_id=pr.public_id,
                    prospect_name=pr.display_name,
                    day=pr.converted_at.astimezone(ZoneInfo(get_settings().timezone)).date() if pr.converted_at else None,
                    amount=None,
                    description=None,
                    status="Cliente",
                    seller=pr.owner.full_name if pr.owner else None,
                )
            )
    else:
        raise AppError("Indicador no válido.", code="INVALID_KEY")
    return items
