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
from app.modules.imports.schemas import ImportJobDetailRead, ImportJobRead, ImportPreview, WeeklyReport, WeeklyReportFilters
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


@router.get("/reports/weekly", response_model=WeeklyReport)
def weekly_report(
    service: ReportServiceDep,
    user: CurrentUser,
    date: str | None = None,
) -> WeeklyReport:
    return service.build(WeeklyReportFilters(date=date), user)


@router.get("/reports/weekly/export")
def weekly_report_export(
    db: DbSession,
    user: CurrentUser,
    report_date: str | None = None,
) -> StreamingResponse:
    target = datetime.strptime(report_date, "%Y-%m-%d").date() if report_date else date.today()
    data = WeeklyReportExporter(db).export(target, user)
    filename = f"FOR-VEN-001_{target.strftime('%Y-%m-%d')}.xlsx"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
