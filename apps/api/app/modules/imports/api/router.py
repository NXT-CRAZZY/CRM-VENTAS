from datetime import date, datetime
from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import StreamingResponse

import tempfile
from pathlib import Path

from app.core.deps import CurrentUser, DbSession, require
from app.modules.imports.application.exporter import WeeklyReportExporter
from app.modules.imports.application.use_cases import ImportService, WeeklyReportService
from app.modules.imports.infrastructure.models import ImportJob
from app.modules.imports.schemas import ImportJobDetailRead, ImportJobRead, ImportPreview, WeeklyDetailItem, WeeklyReport, WeeklyReportFilters
from app.modules.rbac.domain.permissions import P

router = APIRouter(tags=["Importaciones"])


def _import_service(db: DbSession) -> ImportService:
    return ImportService(db)


def _report_service(db: DbSession) -> WeeklyReportService:
    return WeeklyReportService(db)


ImportServiceDep = Annotated[ImportService, Depends(_import_service)]
ReportServiceDep = Annotated[WeeklyReportService, Depends(_report_service)]


@router.post(
    "/imports/for-ven-001/preview",
    response_model=ImportPreview,
    dependencies=[Depends(require(P.IMPORT_RUN))],
)
def preview_for_ven_001(
    file: Annotated[UploadFile, File(...)],
    service: ImportServiceDep,
) -> ImportPreview:
    suffix = Path(file.filename or "import.xlsx").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        path = Path(tmp.name)
    return service.preview(path, file.filename or "import.xlsx")


@router.post(
    "/imports/for-ven-001",
    response_model=ImportJobDetailRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require(P.IMPORT_RUN))],
)
def import_for_ven_001(
    file: Annotated[UploadFile, File(...)],
    service: ImportServiceDep,
    user: CurrentUser,
) -> ImportJob:
    suffix = Path(file.filename or "import.xlsx").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        path = Path(tmp.name)
    job = service.import_file(path, file.filename or "import.xlsx", user)
    return job


@router.get("/imports", response_model=list[ImportJobRead], dependencies=[Depends(require(P.IMPORT_RUN))])
def list_imports(service: ImportServiceDep, user: CurrentUser) -> list[ImportJob]:
    return service.list_jobs(user)


@router.get("/imports/{job_id}", response_model=ImportJobDetailRead)
def get_import(job_id: UUID, service: ImportServiceDep, user: CurrentUser) -> ImportJob:
    return service.get_job(job_id, user)


def _filters(
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    seller_id: str | None = None,
    product_id: str | None = None,
    type_id: str | None = None,
) -> WeeklyReportFilters:
    return WeeklyReportFilters(
        date=date, date_from=date_from, date_to=date_to, seller_id=seller_id, product_id=product_id, type_id=type_id
    )


Filters = Annotated[WeeklyReportFilters, Depends(_filters)]


@router.get("/reports/weekly", response_model=WeeklyReport)
def weekly_report(service: ReportServiceDep, user: CurrentUser, filters: Filters) -> WeeklyReport:
    return service.build(filters, user)


@router.get("/reports/weekly/detail", response_model=list[WeeklyDetailItem])
def weekly_report_detail(
    service: ReportServiceDep, user: CurrentUser, filters: Filters, key: str, period: str = "month"
) -> list[WeeklyDetailItem]:
    return service.detail(filters, user, key, period)


@router.get("/reports/weekly/export")
def weekly_report_export(db: DbSession, user: CurrentUser, filters: Filters) -> StreamingResponse:
    from app.modules.imports.application.weekly import local_today

    target = datetime.strptime(filters.date, "%Y-%m-%d").date() if filters.date else local_today()
    data = WeeklyReportExporter(db).export(target, user, filters)
    filename = f"FOR-VEN-001_{target.strftime('%Y-%m-%d')}.xlsx"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
