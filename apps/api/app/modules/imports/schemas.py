from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.schemas import ApiModel


class ImportJobRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    filename: str
    sheet_name: str | None
    status: str
    total_rows: int
    processed_rows: int
    created_prospects: int
    updated_prospects: int
    created_interactions: int
    created_opportunities: int
    created_at: datetime
    updated_at: datetime


class ImportRowErrorRead(ApiModel):
    row_number: int
    field: str | None
    message: str
    raw_data: dict


class ImportJobDetailRead(ImportJobRead):
    errors: list[ImportRowErrorRead]


class ImportPreviewRow(BaseModel):
    row_number: int
    ruc: str | None
    name: str | None
    contact: str | None
    email: str | None
    phone: str | None
    channel_code: str | None
    occurred_at: datetime | None
    mode_code: str | None
    attempt: int | None
    interest_code: str | None
    result_code: str | None
    amount: float | None
    sold_code: str | None
    notes: str | None
    valid: bool
    errors: list[str]


class ImportPreview(BaseModel):
    filename: str
    sheet_name: str | None
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[ImportPreviewRow]


class WeeklyReportRow(BaseModel):
    label: str
    today: int | float
    month: int | float


class WeeklyReport(BaseModel):
    generated_at: datetime
    quotes_today: int
    quotes_month: int
    sales_today: float
    sales_month: float
    sales_update_today: float
    sales_update_month: float
    sales_new_today: float
    sales_new_month: float
    new_clients_today: int
    new_clients_month: int
    rows: list[WeeklyReportRow]


class WeeklyReportFilters(BaseModel):
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
