from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.modules.catalogs.infrastructure.models import CatalogOption
from app.modules.imports.application.parser import parse_for_ven_001
from app.modules.imports.infrastructure.models import ImportJob, ImportRowError
from app.modules.imports.schemas import ImportJobDetailRead, ImportPreview, ImportPreviewRow, WeeklyReport, WeeklyReportFilters, WeeklyReportRow
from app.modules.interactions.infrastructure.models import Interaction
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.prospects.infrastructure.models import Prospect, ProspectContact, ProspectStatusHistory
from app.modules.rbac.domain.permissions import P
from app.modules.users.infrastructure.models import User
from app.shared.documents import is_valid_ruc, ruc_person_type


class ImportService:
    def __init__(self, session: Session) -> None:
        self.s = session
        self._catalogs: dict[str, dict[str, int]] | None = None

    def _load_catalogs(self) -> dict[str, dict[str, int]]:
        if self._catalogs is not None:
            return self._catalogs
        options = self.s.scalars(select(CatalogOption).where(CatalogOption.is_active.is_(True)))
        out: dict[str, dict[str, int]] = {}
        for opt in options:
            code = opt.catalog.code if opt.catalog else None
            if not code:
                continue
            out.setdefault(code, {})[opt.code] = opt.id
            if opt.legacy_code:
                out.setdefault(code, {})[opt.legacy_code] = opt.id
        self._catalogs = out
        return out

    def _option_id(self, catalog_code: str, key: str | None) -> int | None:
        if not key:
            return None
        return self._load_catalogs().get(catalog_code, {}).get(key.upper())

    def _serialize_raw_data(self, row: dict) -> dict:
        out: dict = {}
        for k, v in row.items():
            if k == "raw" or v is None:
                continue
            if isinstance(v, datetime):
                out[k] = v.isoformat()
            else:
                out[k] = v
        return out

    def _validate_row(self, row: dict) -> list[str]:
        errors: list[str] = []
        if not row.get("ruc"):
            errors.append("El RUC es obligatorio.")
        elif not is_valid_ruc(str(row["ruc"])):
            errors.append("El RUC no es válido.")
        if not row.get("name"):
            errors.append("La razón social es obligatoria.")
        if row.get("when") is None and row.get("result_code"):
            errors.append("La fecha y hora de contacto no es válida.")
        if row.get("result_code") == "V" and row.get("amount") is None:
            errors.append("El monto de venta es obligatorio cuando el logro es Venta.")
        return errors

    def preview(self, path: Path, filename: str) -> ImportPreview:
        raw_rows, file_errors = parse_for_ven_001(path)
        if file_errors:
            return ImportPreview(
                filename=filename,
                sheet_name=None,
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                rows=[],
            )

        rows: list[ImportPreviewRow] = []
        valid = 0
        invalid = 0
        for row in raw_rows:
            errors = self._validate_row(row)
            if errors:
                invalid += 1
            else:
                valid += 1
            rows.append(
                ImportPreviewRow(
                    row_number=row["row_number"],
                    ruc=row["ruc"],
                    name=row["name"],
                    contact=row["contact"],
                    email=row["email"],
                    phone=row["phone"],
                    channel_code=row["channel_code"],
                    occurred_at=row["when"],
                    mode_code=row["mode_code"],
                    attempt=row["attempt"],
                    interest_code=row["interest_code"],
                    result_code=row["result_code"],
                    amount=row["amount"],
                    sold_code=row["sold_code"],
                    notes=row["notes"],
                    valid=not errors,
                    errors=errors,
                )
            )
        return ImportPreview(
            filename=filename,
            sheet_name=None,
            total_rows=len(rows),
            valid_rows=valid,
            invalid_rows=invalid,
            rows=rows,
        )

    def import_file(self, path: Path, filename: str, actor: User) -> ImportJob:
        raw_rows, file_errors = parse_for_ven_001(path)
        job = ImportJob(filename=filename, sheet_name=None, created_by_id=actor.id, status="PROCESSING")
        self.s.add(job)
        self.s.flush()

        if file_errors:
            for msg in file_errors:
                self.s.add(ImportRowError(import_job_id=job.id, row_number=0, message=msg, raw_data={}))
            job.status = "FAILED"
            self.s.flush()
            return job

        job.total_rows = len(raw_rows)
        seen_rucs: dict[str, Prospect] = {}

        for row in raw_rows:
            row_errors = self._validate_row(row)
            if row_errors:
                for msg in row_errors:
                    self.s.add(
                        ImportRowError(
                            import_job_id=job.id,
                            row_number=row["row_number"],
                            message=msg,
                            raw_data=self._serialize_raw_data(row),
                        )
                    )
                continue

            ruc = str(row["ruc"]).strip()
            prospect = seen_rucs.get(ruc)
            if prospect is None:
                existing = self.s.scalar(select(Prospect).where(Prospect.document_number == ruc, Prospect.deleted_at.is_(None)))
                if existing:
                    prospect = self._update_prospect_from_row(existing, row)
                    job.updated_prospects += 1
                else:
                    prospect = self._create_prospect_from_row(row, actor)
                    job.created_prospects += 1
                seen_rucs[ruc] = prospect

            self._create_interaction(prospect, row, actor)
            job.created_interactions += 1

            if row.get("result_code") == "V" and row.get("amount"):
                self._create_sale_opportunity(prospect, row, actor)
                job.created_opportunities += 1

            job.processed_rows += 1

        job.status = "COMPLETED" if job.processed_rows == job.total_rows else "COMPLETED_WITH_ERRORS"
        self.s.flush()
        return job

    def _create_prospect_from_row(self, row: dict, actor: User) -> Prospect:
        ruc = str(row["ruc"]).strip()
        person_type = ruc_person_type(ruc)
        doc_type_id = self._option_id("document_type", "RUC")
        interest_id = self._option_id("interest_level", row.get("interest_code"))
        channel_id = self._option_id("contact_channel", row.get("channel_code"))

        # Calcular prioridad desde el nivel de interés
        priority_id = None
        if row.get("interest_code"):
            priority_map = {"ALTO": "ALTA", "REGULAR": "MEDIA", "BAJO": "BAJA"}
            priority_id = self._option_id("priority", priority_map.get(row["interest_code"].upper()))

        prospect = Prospect(
            code=self._next_prospect_code(),
            person_type=person_type,
            document_type_id=doc_type_id,
            document_number=ruc,
            legal_name=row["name"],
            trade_name=row["name"],
            display_name=row["name"],
            email=row.get("email"),
            phone=row.get("phone"),
            address=row.get("address"),
            interest_level_id=interest_id,
            priority_id=priority_id,
            acquisition_channel_id=channel_id,
            source_id=self._option_id("prospect_source", "OTRO"),
            owner_id=actor.id,
            status="ACTIVO",
            relationship_type="PROSPECTO",
            legacy_source="FOR-VEN-001",
            legacy_row=row.get("number"),
        )
        if row.get("contact"):
            prospect.contacts.append(
                ProspectContact(
                    full_name=row["contact"],
                    email=row.get("email"),
                    phone=row.get("phone"),
                    is_primary=True,
                )
            )
        self.s.add(prospect)
        self.s.flush()
        self.s.add(
            ProspectStatusHistory(
                prospect_id=prospect.id,
                to_relationship_type=prospect.relationship_type,
                to_status=prospect.status,
                changed_by_id=actor.id,
                reason="Importación FOR-VEN-001",
            )
        )
        return prospect

    def _update_prospect_from_row(self, prospect: Prospect, row: dict) -> Prospect:
        if row.get("email") and not prospect.email:
            prospect.email = row["email"]
        if row.get("phone") and not prospect.phone:
            prospect.phone = row["phone"]
        if row.get("address") and not prospect.address:
            prospect.address = row["address"]
        if row.get("interest_code"):
            prospect.interest_level_id = self._option_id("interest_level", row["interest_code"]) or prospect.interest_level_id
        return prospect

    def _create_interaction(self, prospect: Prospect, row: dict, actor: User) -> None:
        when = row.get("when") or datetime.combine(date.today(), time.min)
        channel_id = self._option_id("contact_channel", row.get("channel_code")) or self._option_id("contact_channel", "OTRO")
        mode_id = self._option_id("contact_mode", row.get("mode_code"))
        result_id = self._option_id("contact_result", row.get("result_code")) or self._option_id("contact_result", "CONTESTO")
        interest_id = self._option_id("interest_level", row.get("interest_code"))

        interaction = Interaction(
            prospect_id=prospect.id,
            user_id=actor.id,
            occurred_at=when,
            channel_id=channel_id,
            mode_id=mode_id,
            result_id=result_id,
            interest_level_id=interest_id,
            attempt_number=row.get("attempt") or 1,
            notes=row.get("notes"),
            stage_before=prospect.status,
            stage_after=prospect.status,
        )
        prospect.last_contact_at = when
        prospect.interaction_count = (prospect.interaction_count or 0) + 1
        if prospect.first_contact_at is None or when < prospect.first_contact_at:
            prospect.first_contact_at = when
        self.s.add(interaction)

    def _create_sale_opportunity(self, prospect: Prospect, row: dict, actor: User) -> None:
        stage_id = self._option_id("pipeline_stage", "CERRADO_GANADO")
        type_id = self._option_id("opportunity_type", row.get("sold_code")) or self._option_id("opportunity_type", "NUEVO")
        when = row.get("when") or datetime.now()

        opportunity = Opportunity(
            prospect_id=prospect.id,
            stage_id=stage_id,
            type_id=type_id,
            owner_id=actor.id,
            title=f"Venta {row.get('sold_code') or 'NUEVO'} - {prospect.display_name}",
            description=row.get("notes"),
            estimated_amount=Decimal(str(row["amount"])),
            probability=100,
            expected_close_date=when.date(),
            actual_close_date=when.date(),
        )
        if prospect.relationship_type != "CLIENTE":
            prospect.relationship_type = "CLIENTE"
            prospect.converted_at = when
            prospect.converted_by_id = actor.id
        self.s.add(opportunity)

    def _next_prospect_code(self) -> str:
        prefix = "PROS-"
        max_code = self.s.scalar(select(func.max(Prospect.code)).where(Prospect.code.like(f"{prefix}%")))
        if max_code:
            try:
                n = int(max_code.replace(prefix, ""))
            except ValueError:
                n = 0
        else:
            n = 0
        return f"{prefix}{n + 1:06d}"

    def get_job(self, public_id: UUID, user: User) -> ImportJob:
        job = self.s.scalar(select(ImportJob).where(ImportJob.public_id == public_id))
        if job is None:
            raise NotFoundError("El trabajo de importación no existe.")
        if P.PROSPECTS_READ_ALL not in user.permission_codes and job.created_by_id != user.id:
            raise ForbiddenError("No tienes acceso a este trabajo de importación.")
        return job

    def list_jobs(self, user: User) -> list[ImportJob]:
        stmt = select(ImportJob).order_by(ImportJob.created_at.desc())
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            stmt = stmt.where(ImportJob.created_by_id == user.id)
        return list(self.s.scalars(stmt))


class WeeklyReportService:
    def __init__(self, session: Session) -> None:
        self.s = session

    def build(self, filters: WeeklyReportFilters, user: User) -> WeeklyReport:
        target = self._parse_date(filters.date) if filters.date else date.today()
        start_of_month = target.replace(day=1)
        next_day = target + timedelta(days=1)

        result_ids = self._result_ids()
        stage_won_id = self._stage_won_id()

        quotes_today = self._count_interactions(target, next_day, result_ids.get("COTIZACION"))
        quotes_month = self._count_interactions(start_of_month, next_day, result_ids.get("COTIZACION"))

        sales_today, sales_update_today, sales_new_today = self._sales_summary(target, next_day, stage_won_id)
        sales_month, sales_update_month, sales_new_month = self._sales_summary(start_of_month, next_day, stage_won_id)

        new_clients_today = self._count_new_clients(target, next_day)
        new_clients_month = self._count_new_clients(start_of_month, next_day)

        rows = [
            WeeklyReportRow(label="Cotizaciones", today=quotes_today, month=quotes_month),
            WeeklyReportRow(label="Ventas totales", today=sales_today, month=sales_month),
            WeeklyReportRow(label="Ventas actualización", today=sales_update_today, month=sales_update_month),
            WeeklyReportRow(label="Ventas nuevas", today=sales_new_today, month=sales_new_month),
            WeeklyReportRow(label="Nuevos clientes", today=new_clients_today, month=new_clients_month),
        ]

        return WeeklyReport(
            generated_at=datetime.now(),
            quotes_today=quotes_today,
            quotes_month=quotes_month,
            sales_today=sales_today,
            sales_month=sales_month,
            sales_update_today=sales_update_today,
            sales_update_month=sales_update_month,
            sales_new_today=sales_new_today,
            sales_new_month=sales_new_month,
            new_clients_today=new_clients_today,
            new_clients_month=new_clients_month,
            rows=rows,
        )

    def _parse_date(self, value: str) -> date:
        return datetime.strptime(value, "%Y-%m-%d").date()

    def _result_ids(self) -> dict[str, int]:
        return {
            opt.code: opt.id
            for opt in self.s.scalars(
                select(CatalogOption).join(CatalogOption.catalog).where(CatalogOption.catalog.has(code="contact_result"))
            )
        }

    def _stage_won_id(self) -> int | None:
        return self.s.scalar(
            select(CatalogOption.id).join(CatalogOption.catalog).where(CatalogOption.catalog.has(code="pipeline_stage"), CatalogOption.code == "CERRADO_GANADO")
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
            select(CatalogOption.id).join(CatalogOption.catalog).where(CatalogOption.catalog.has(code="opportunity_type"), CatalogOption.code == "ACTUALIZACION")
        )
        nuevo_id = self.s.scalar(
            select(CatalogOption.id).join(CatalogOption.catalog).where(CatalogOption.catalog.has(code="opportunity_type"), CatalogOption.code == "NUEVO")
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
