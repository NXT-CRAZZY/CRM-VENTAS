from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SalesDashboardRead(BaseModel):
    tasks_today: int
    tasks_overdue: int
    new_prospects_this_week: int
    follow_ups_today: int
    prospects_without_contact: int
    high_interest_prospects: int
    upcoming_actions: list["UpcomingActionRead"]


class UpcomingActionRead(BaseModel):
    prospect_id: UUID
    prospect_name: str
    action_type: str
    due_at: datetime | None


class PipelineStageSummary(BaseModel):
    stage_id: UUID
    stage_name: str
    stage_code: str
    count: int
    estimated_amount: float
    color: str | None


class TopPerformer(BaseModel):
    user_id: UUID
    full_name: str
    won_count: int
    won_amount: float


class TopProduct(BaseModel):
    product_id: UUID
    product_name: str
    quote_count: int
    total_amount: float


class ConversionSummary(BaseModel):
    total_prospects: int
    converted_to_client: int
    conversion_rate: float


class ManagementDashboardRead(BaseModel):
    generated_at: datetime
    pipeline: list[PipelineStageSummary]
    sales_this_month: float
    sales_last_month: float
    new_clients_this_month: int
    new_clients_last_month: int
    conversion: ConversionSummary
    top_performers: list[TopPerformer]
    top_products: list[TopProduct]
