"""Exportación del informe semanal a Excel (formato inspirado en FOR-VEN-001)."""

from datetime import date, datetime, time, timedelta
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.interactions.infrastructure.models import Interaction
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.users.infrastructure.models import User


class WeeklyReportExporter:
    def __init__(self, session: Session) -> None:
        self.s = session

    @staticmethod
    def _naive(value: Any) -> Any:
        if isinstance(value, datetime) and value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value

    def export(self, target: date | None, user: User) -> bytes:
        target = target or date.today()
        start_of_month = target.replace(day=1)
        next_day = target + timedelta(days=1)

        wb = Workbook()
        self._build_summary_sheet(wb.active, target, start_of_month, next_day)
        self._build_prospects_sheet(wb.create_sheet("Prospectos"), target, start_of_month, next_day, user)
        self._build_opportunities_sheet(wb.create_sheet("Oportunidades"), start_of_month, next_day, user)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def _build_summary_sheet(self, ws, target: date, start_of_month: date, next_day: date) -> None:
        ws.title = "Resumen"

        # Encabezado estilo FOR-VEN-001
        ws.merge_cells("B1:F1")
        ws["B1"] = "INFORME SEMANAL DE VENTAS"
        ws["B1"].font = Font(bold=True, size=16, color="1F2937")
        ws["B1"].alignment = Alignment(horizontal="center")

        ws["P1"] = "CÓDIGO: FOR-VEN-001"
        ws["P2"] = f"FECHA: {target.strftime('%d-%m-%Y')}"
        ws["P3"] = "PÁGINA: 1 de 1"
        ws["P4"] = "VERSIÓN: 03"

        ws["B6"] = "Fecha de informe"
        ws["C6"] = target
        ws["C6"].number_format = "DD/MM/YYYY"

        # Tabla resumen
        header_fill = PatternFill(start_color="E5E7EB", end_color="E5E7EB", fill_type="solid")
        header_font = Font(bold=True, color="374151")
        thin_border = Border(
            left=Side(style="thin", color="D1D5DB"),
            right=Side(style="thin", color="D1D5DB"),
            top=Side(style="thin", color="D1D5DB"),
            bottom=Side(style="thin", color="D1D5DB"),
        )

        headers = ["Indicador", "Hoy (S/.) / und", "Acumulado del mes (S/.) / und"]
        for col, text in enumerate(headers, 2):
            cell = ws.cell(row=8, column=col, value=text)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", wrap_text=True)

        result_ids = self._result_ids()
        stage_won_id = self._stage_won_id()

        quotes_today = self._count_interactions(target, next_day, result_ids.get("COTIZACION"))
        quotes_month = self._count_interactions(start_of_month, next_day, result_ids.get("COTIZACION"))
        sales_today, _, _ = self._sales_summary(target, next_day, stage_won_id)
        sales_month, _, _ = self._sales_summary(start_of_month, next_day, stage_won_id)
        new_clients_today = self._count_new_clients(target, next_day)
        new_clients_month = self._count_new_clients(start_of_month, next_day)

        rows = [
            ("TOTAL DE COTIZACIONES", quotes_today, quotes_month),
            ("TOTAL DE VENTAS", sales_today, sales_month),
            ("NUEVOS CLIENTES", new_clients_today, new_clients_month),
        ]

        for r_idx, (label, today, month) in enumerate(rows, 9):
            ws.cell(row=r_idx, column=2, value=label).border = thin_border
            ws.cell(row=r_idx, column=3, value=today).border = thin_border
            ws.cell(row=r_idx, column=4, value=month).border = thin_border

        self._auto_width(ws)

    def _build_prospects_sheet(self, ws, target: date, start_of_month: date, next_day: date, user: User) -> None:
        ws.title = "Prospectos"

        headers = [
            "Nro",
            "RUC/DNI",
            "Razón Social / Nombre",
            "Dirección",
            "Contacto",
            "Email",
            "Teléfono",
            "Forma de contacto",
            "Fecha contacto",
            "Intento",
            "Nivel de interés",
            "Logro",
            "Monto venta",
            "Producto vendido",
            "Observaciones",
        ]
        self._write_header(ws, headers)

        accessible_filter = True
        if "prospects.read_all" not in user.permission_codes:
            accessible_filter = Prospect.owner_id == user.id

        prospects = self.s.scalars(
            select(Prospect)
            .where(
                Prospect.deleted_at.is_(None),
                accessible_filter,
            )
            .order_by(Prospect.created_at.desc())
            .limit(500)
        ).all()

        for idx, p in enumerate(prospects, 1):
            last_interaction = self._last_interaction(p.id)
            row = [
                idx,
                p.document_number,
                p.display_name,
                p.address,
                p.contacts[0].full_name if p.contacts else None,
                p.email,
                p.phone,
                last_interaction.get("channel") if last_interaction else None,
                last_interaction.get("occurred_at") if last_interaction else None,
                last_interaction.get("attempt") if last_interaction else p.interaction_count,
                last_interaction.get("interest") if last_interaction else None,
                last_interaction.get("result") if last_interaction else None,
                last_interaction.get("amount") if last_interaction else None,
                last_interaction.get("product") if last_interaction else None,
                last_interaction.get("notes") if last_interaction else None,
            ]
            self._write_row(ws, idx + 1, row)

        self._auto_width(ws)

    def _build_opportunities_sheet(self, ws, start_of_month: date, next_day: date, user: User) -> None:
        ws.title = "Oportunidades"

        headers = [
            "Nro",
            "Prospecto",
            "Título",
            "Etapa",
            "Tipo",
            "Monto estimado",
            "Probabilidad",
            "Fecha cierre esperado",
            "Fecha cierre real",
            "Vendedor",
        ]
        self._write_header(ws, headers)

        accessible_filter = True
        if "prospects.read_all" not in user.permission_codes:
            accessible_filter = Prospect.owner_id == user.id

        opportunities = self.s.scalars(
            select(Opportunity)
            .join(Prospect)
            .where(
                Opportunity.deleted_at.is_(None),
                Opportunity.created_at >= datetime.combine(start_of_month, time.min),
                Opportunity.created_at < datetime.combine(next_day, time.min),
                accessible_filter,
            )
            .order_by(Opportunity.created_at.desc())
            .limit(500)
        ).all()

        for idx, o in enumerate(opportunities, 1):
            row = [
                idx,
                o.prospect.display_name if o.prospect else None,
                o.title,
                o.stage.name if o.stage else None,
                o.type.name if o.type else None,
                float(o.estimated_amount) if o.estimated_amount else None,
                o.probability,
                o.expected_close_date,
                o.actual_close_date,
                o.owner.full_name if o.owner else None,
            ]
            self._write_row(ws, idx + 1, row)

        self._auto_width(ws)

    def _write_header(self, ws, headers: list[str]) -> None:
        header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style="thin", color="D1D5DB"),
            right=Side(style="thin", color="D1D5DB"),
            top=Side(style="thin", color="D1D5DB"),
            bottom=Side(style="thin", color="D1D5DB"),
        )
        for col, text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=text)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def _write_row(self, ws, row_idx: int, values: list[Any]) -> None:
        thin_border = Border(
            left=Side(style="thin", color="D1D5DB"),
            right=Side(style="thin", color="D1D5DB"),
            top=Side(style="thin", color="D1D5DB"),
            bottom=Side(style="thin", color="D1D5DB"),
        )
        for col, value in enumerate(values, 1):
            value = self._naive(value)
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if isinstance(value, datetime):
                cell.number_format = "DD/MM/YYYY HH:MM"
            elif isinstance(value, date):
                cell.number_format = "DD/MM/YYYY"

    def _auto_width(self, ws) -> None:
        for column_cells in ws.columns:
            length = max(len(str(cell.value or "")) for cell in column_cells)
            ws.column_dimensions[get_column_letter(column_cells[0].column)].width = min(length + 4, 50)

    def _last_interaction(self, prospect_id: int) -> dict[str, Any] | None:
        interaction = self.s.scalar(
            select(Interaction)
            .where(
                Interaction.prospect_id == prospect_id,
                Interaction.deleted_at.is_(None),
            )
            .order_by(Interaction.occurred_at.desc())
        )
        if interaction is None:
            return None
        return {
            "channel": interaction.channel.name if interaction.channel else None,
            "occurred_at": self._naive(interaction.occurred_at),
            "attempt": interaction.attempt_number,
            "interest": interaction.interest_level.name if interaction.interest_level else None,
            "result": interaction.result.name if interaction.result else None,
            "amount": float(interaction.amount) if getattr(interaction, "amount", None) else None,
            "product": None,
            "notes": interaction.notes,
        }

    def _result_ids(self) -> dict[str, int]:
        return {
            opt.code: opt.id
            for opt in self.s.scalars(
                select(CatalogOption).join(Catalog).where(Catalog.code == "contact_result")
            )
        }

    def _stage_won_id(self) -> int | None:
        return self.s.scalar(
            select(CatalogOption.id).join(Catalog).where(Catalog.code == "pipeline_stage", CatalogOption.code == "CERRADO_GANADO")
        )

    def _count_interactions(self, start: date, end: date, result_id: int | None) -> int:
        if result_id is None:
            return 0
        return self.s.scalar(
            select(func.count(Interaction.id)).where(
                Interaction.result_id == result_id,
                Interaction.occurred_at >= datetime.combine(start, time.min),
                Interaction.occurred_at < datetime.combine(end, time.min),
                Interaction.deleted_at.is_(None),
            )
        ) or 0

    def _sales_summary(self, start: date, end: date, stage_won_id: int | None) -> tuple[float, float, float]:
        if stage_won_id is None:
            return 0.0, 0.0, 0.0
        actualizacion_id = self.s.scalar(
            select(CatalogOption.id).join(Catalog).where(Catalog.code == "opportunity_type", CatalogOption.code == "ACTUALIZACION")
        )
        nuevo_id = self.s.scalar(
            select(CatalogOption.id).join(Catalog).where(Catalog.code == "opportunity_type", CatalogOption.code == "NUEVO")
        )

        rows = self.s.execute(
            select(Opportunity.estimated_amount, Opportunity.type_id).where(
                Opportunity.stage_id == stage_won_id,
                Opportunity.actual_close_date >= start,
                Opportunity.actual_close_date < end,
                Opportunity.deleted_at.is_(None),
            )
        ).all()

        total = sum(float(r.estimated_amount or 0) for r in rows)
        update = sum(float(r.estimated_amount or 0) for r in rows if r.type_id == actualizacion_id)
        new = sum(float(r.estimated_amount or 0) for r in rows if r.type_id == nuevo_id)
        return total, update, new

    def _count_new_clients(self, start: date, end: date) -> int:
        return self.s.scalar(
            select(func.count(Prospect.id)).where(
                Prospect.relationship_type == "CLIENTE",
                Prospect.converted_at >= datetime.combine(start, time.min),
                Prospect.converted_at < datetime.combine(end, time.min),
            )
        ) or 0
