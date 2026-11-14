"""Exportación del informe de ventas a Excel.

El archivo refleja exactamente lo que se ve en pantalla: mismo periodo, mismos filtros y mismos
números. Hojas: Resumen (indicadores y filtros aplicados), Cotizaciones, Ventas y Nuevos clientes
(cada una con el detalle fila por fila y su total).
"""

from datetime import date, datetime
from io import BytesIO
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.catalogs.infrastructure.models import CatalogOption
from app.modules.imports.application.weekly import (
    _client_filter,
    _context,
    _quote_filter,
    _sale_filter,
    _won_id,
    build_weekly_report,
)
from app.modules.imports.schemas import WeeklyReportFilters
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.products.infrastructure.models import Product
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.quotes.infrastructure.models import Quote
from app.modules.users.infrastructure.models import User

BRAND = "E03E0F"
INK = "1F2937"
GRID = "D1D5DB"
SOFT = "F9FAFB"
MONEY = '"S/ "#,##0.00'
THIN = Side(style="thin", color=GRID)
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

QUOTE_STATUS = {"SENT": "Enviada", "ACCEPTED": "Aceptada", "REJECTED": "Rechazada", "DRAFT": "Borrador"}


class WeeklyReportExporter:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.tz = ZoneInfo(get_settings().timezone)

    # ---------- utilidades ----------
    def _local_date(self, value: datetime | None) -> date | None:
        return value.astimezone(self.tz).date() if value else None

    def _title(self, ws, text: str, subtitle: str, width: int) -> None:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
        ws.cell(row=1, column=1, value=text).font = Font(bold=True, size=16, color=BRAND)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
        ws.cell(row=2, column=1, value=subtitle).font = Font(italic=True, size=10, color="6B7280")
        ws.row_dimensions[1].height = 24

    def _header(self, ws, row: int, headers: list[str]) -> None:
        for col, text in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=text)
            cell.fill = PatternFill("solid", start_color=BRAND, end_color=BRAND)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = BORDER
        ws.row_dimensions[row].height = 22

    def _row(self, ws, row: int, values: list[Any], money_cols: set[int] = frozenset(), zebra: bool = False) -> None:
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True, horizontal="right" if col in money_cols else None)
            if zebra:
                cell.fill = PatternFill("solid", start_color=SOFT, end_color=SOFT)
            if isinstance(value, datetime):
                cell.number_format = "DD/MM/YYYY HH:MM"
            elif isinstance(value, date):
                cell.number_format = "DD/MM/YYYY"
            elif col in money_cols:
                cell.number_format = MONEY

    def _total_row(self, ws, row: int, ncols: int, label_col: int, label: str, money_col: int, total: float) -> None:
        for col in range(1, ncols + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = BORDER
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", start_color="FDE8E1", end_color="FDE8E1")
        ws.cell(row=row, column=label_col, value=label).alignment = Alignment(horizontal="right")
        cell = ws.cell(row=row, column=money_col, value=total)
        cell.number_format = MONEY
        cell.alignment = Alignment(horizontal="right")

    def _finish(self, ws, widths: list[int], header_row: int, last_row: int, ncols: int) -> None:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
        if last_row > header_row:
            ws.auto_filter.ref = f"A{header_row}:{get_column_letter(ncols)}{last_row}"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.sheet_view.showGridLines = False

    # ---------- exportación ----------
    def export(self, target: date | None, user: User, filters: WeeklyReportFilters | None = None) -> bytes:
        f = filters or WeeklyReportFilters()
        if not (f.date_from or f.date_to):  # sin rango: el mes de la fecha indicada
            ref = target or datetime.now(self.tz).date()
            f = f.model_copy(update={"date_from": ref.replace(day=1).isoformat(), "date_to": ref.isoformat()})
        report = build_weekly_report(self.s, user, f)
        ctx = _context(self.s, user, f)
        period = ctx.periods["range"]
        subtitle = f"Periodo: {report.range_label}  ·  Generado: {datetime.now(self.tz).strftime('%d/%m/%Y %H:%M')}  ·  Usuario: {user.full_name}"

        wb = Workbook()
        self._summary(wb.active, report, f, subtitle, user, ctx)
        self._quotes(wb.create_sheet("Cotizaciones"), ctx, period, subtitle)
        self._sales(wb.create_sheet("Ventas"), ctx, period, subtitle)
        self._clients(wb.create_sheet("Nuevos clientes"), ctx, period, subtitle)

        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def _filter_lines(self, f: WeeklyReportFilters, user: User, ctx) -> list[tuple[str, str]]:
        if not ctx.see_all:
            seller = f"Solo mis datos ({user.full_name})"
        elif f.seller_id:
            name = self.s.scalar(select(User.full_name).where(User.public_id == UUID(f.seller_id)))
            seller = name or "—"
        else:
            seller = "Todo el equipo"
        product = "Todos"
        if f.product_id:
            product = self.s.scalar(select(Product.name).where(Product.public_id == UUID(f.product_id))) or "—"
        sale_type = "Todos"
        if f.type_id:
            sale_type = self.s.scalar(select(CatalogOption.name).where(CatalogOption.public_id == UUID(f.type_id))) or "—"
        return [("Vendedor", seller), ("Producto", product), ("Tipo de venta", sale_type)]

    def _summary(self, ws, report, f, subtitle: str, user: User, ctx) -> None:
        ws.title = "Resumen"
        self._title(ws, "INFORME DE VENTAS", subtitle, 3)
        ws.cell(row=4, column=1, value="Filtros aplicados").font = Font(bold=True, color=INK)
        r = 5
        for label, value in self._filter_lines(f, user, ctx):
            ws.cell(row=r, column=1, value=label).font = Font(color="6B7280")
            ws.cell(row=r, column=2, value=value).font = Font(bold=True)
            r += 1
        r += 1
        header_row = r
        self._header(ws, header_row, ["Indicador", "Total del periodo"])
        r += 1
        first = r
        for i, row in enumerate(report.rows):
            sub = row.label.startswith("   ")
            value = row.range if row.range is not None else 0
            self._row(ws, r, [("      " if sub else "") + row.label.strip(), value], {2} if row.kind == "money" else set(), zebra=i % 2 == 1)
            if not sub:
                ws.cell(row=r, column=1).font = Font(bold=True)
            if row.kind == "count":
                ws.cell(row=r, column=2).alignment = Alignment(horizontal="right")
            r += 1
        self._finish(ws, [38, 24, 4], header_row, r - 1, 2)
        ws.auto_filter.ref = None
        ws.freeze_panes = None
        ws.cell(row=r + 1, column=1, value="Producto y tipo de venta no se aplican a «Nuevos clientes».").font = Font(italic=True, size=9, color="6B7280")

    def _quotes(self, ws, ctx, period, subtitle: str) -> None:
        headers = ["N°", "Fecha de envío", "Cliente", "Documento", "Vendedor", "Estado", "Productos", "Vence", "Monto"]
        self._title(ws, "Cotizaciones enviadas", subtitle, len(headers))
        self._header(ws, 4, headers)
        quotes = self.s.scalars(
            select(Quote).where(*_quote_filter(ctx, period)).order_by(Quote.sent_at.asc())
        ).unique().all()
        r = 5
        for i, q in enumerate(quotes, 1):
            self._row(
                ws,
                r,
                [
                    i,
                    self._local_date(q.sent_at),
                    q.prospect.display_name,
                    q.prospect.document_number,
                    q.prospect.owner.full_name if q.prospect.owner else None,
                    QUOTE_STATUS.get(q.status, q.status),
                    ", ".join(it.description for it in q.items),
                    q.expiration_date,
                    float(q.total),
                ],
                {9},
                zebra=i % 2 == 0,
            )
            r += 1
        self._total_row(ws, r, len(headers), 8, "TOTAL COTIZADO", 9, sum(float(q.total) for q in quotes))
        self._finish(ws, [6, 14, 34, 14, 24, 12, 50, 12, 16], 4, r - 1, len(headers))

    def _sales(self, ws, ctx, period, subtitle: str) -> None:
        headers = ["N°", "Fecha de cierre", "Cliente", "Documento", "Vendedor", "Tipo de venta", "Origen", "Qué se vendió", "Monto"]
        self._title(ws, "Ventas cerradas", subtitle, len(headers))
        self._header(ws, 4, headers)
        opps = self.s.scalars(
            select(Opportunity).where(*_sale_filter(ctx, period, _won_id(self.s))).order_by(Opportunity.actual_close_date.asc(), Opportunity.id.asc())
        ).unique().all()
        r = 5
        for i, o in enumerate(opps, 1):
            accepted = self.s.scalar(
                select(Quote).where(Quote.opportunity_id == o.id, Quote.status == "ACCEPTED", Quote.deleted_at.is_(None))
            )
            what = ", ".join(it.description for it in accepted.items) if accepted and accepted.items else o.title
            self._row(
                ws,
                r,
                [
                    i,
                    o.actual_close_date,
                    o.prospect.display_name,
                    o.prospect.document_number,
                    o.owner.full_name if o.owner else (o.prospect.owner.full_name if o.prospect.owner else None),
                    o.type.name if o.type else "Sin definir",
                    "Con cotización" if accepted else "Sin cotización",
                    what,
                    float(o.estimated_amount) if o.estimated_amount is not None else 0,
                ],
                {9},
                zebra=i % 2 == 0,
            )
            r += 1
        self._total_row(ws, r, len(headers), 8, "TOTAL VENTAS", 9, sum(float(o.estimated_amount or 0) for o in opps))
        self._finish(ws, [6, 14, 34, 14, 24, 24, 16, 50, 16], 4, r - 1, len(headers))

    def _clients(self, ws, ctx, period, subtitle: str) -> None:
        headers = ["N°", "Fecha", "Cliente", "Documento", "Vendedor", "Correo", "Teléfono"]
        self._title(ws, "Nuevos clientes", subtitle, len(headers))
        self._header(ws, 4, headers)
        clients = self.s.scalars(
            select(Prospect).where(*_client_filter(ctx, period)).order_by(Prospect.converted_at.asc())
        ).unique().all()
        r = 5
        for i, p in enumerate(clients, 1):
            self._row(
                ws,
                r,
                [i, self._local_date(p.converted_at), p.display_name, p.document_number, p.owner.full_name if p.owner else None, p.email, p.phone],
                zebra=i % 2 == 0,
            )
            r += 1
        ws.cell(row=r, column=3, value=f"Total: {len(clients)}").font = Font(bold=True)
        self._finish(ws, [6, 14, 34, 14, 24, 30, 16], 4, r - 1, len(headers))
