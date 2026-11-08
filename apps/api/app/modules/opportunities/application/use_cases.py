from datetime import date
from uuid import UUID

from app.core.errors import ForbiddenError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.opportunities.repository import OpportunityRepository
from app.modules.opportunities.schemas import OpportunityCreate, OpportunityRead, OpportunityUpdate
from app.modules.rbac.domain.permissions import P
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams


class OpportunityService:
    def __init__(self, repo: OpportunityRepository, audit: AuditRecorder | None = None) -> None:
        self.repo = repo
        self.audit = audit

    def _resolve_ids(self, data: OpportunityCreate | OpportunityUpdate) -> dict:
        resolved: dict = {}
        if hasattr(data, "owner_id") and data.owner_id:
            resolved["owner_id"] = self._user(data.owner_id)
        if hasattr(data, "stage_id") and data.stage_id:
            resolved["stage_id"] = self._catalog(data.stage_id, "etapa")
        if hasattr(data, "type_id") and data.type_id:
            resolved["type_id"] = self._catalog(data.type_id, "tipo")
        if hasattr(data, "loss_reason_id") and data.loss_reason_id:
            resolved["loss_reason_id"] = self._catalog(data.loss_reason_id, "motivo de pérdida")
        return resolved

    def _user(self, public_id: UUID) -> int:
        internal_id = self.repo.get_user_id(public_id)
        if internal_id is None:
            raise NotFoundError("El responsable no existe.")
        return internal_id

    def _catalog(self, public_id: UUID, label: str) -> int:
        internal_id = self.repo.get_catalog_option_id(public_id)
        if internal_id is None:
            raise NotFoundError(f"{label.capitalize()} no encontrado.")
        return internal_id

    def _prospect(self, public_id: UUID) -> int:
        internal_id = self.repo.get_prospect_id(public_id)
        if internal_id is None:
            raise NotFoundError("El prospecto no existe.")
        return internal_id

    def _enforce_scope(self, opportunity: Opportunity, user: User) -> None:
        if P.PROSPECTS_READ_ALL in user.permission_codes:
            return
        if opportunity.owner_id == user.id:
            return
        raise ForbiddenError("No tienes acceso a esta oportunidad.")

    def list_opportunities(
        self, filters: dict, params: PageParams, user: User
    ) -> Page[OpportunityRead]:
        items, total = self.repo.list_opportunities(filters, params, user)
        return Page(
            items=[OpportunityRead.model_validate(i) for i in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def create_opportunity(self, data: OpportunityCreate, actor: User) -> Opportunity:
        prospect_id = self._prospect(data.prospect_id)
        resolved = self._resolve_ids(data)

        opportunity = Opportunity(
            prospect_id=prospect_id,
            stage_id=resolved["stage_id"],
            type_id=resolved.get("type_id"),
            loss_reason_id=resolved.get("loss_reason_id"),
            owner_id=resolved.get("owner_id"),
            title=data.title,
            description=data.description,
            estimated_amount=data.estimated_amount,
            probability=data.probability,
            expected_close_date=data.expected_close_date,
        )
        self.repo.add(opportunity)

        if self.audit:
            self.audit.record(
                "opportunity.created",
                "opportunity",
                opportunity.public_id,
                label=f"Oportunidad: {opportunity.title}",
                after={"prospect_id": str(data.prospect_id), "stage_id": str(data.stage_id)},
            )

        return opportunity

    def update_opportunity(
        self, public_id: UUID, data: OpportunityUpdate, actor: User
    ) -> Opportunity:
        opportunity = self.repo.get_opportunity(public_id)
        if opportunity is None:
            raise NotFoundError("La oportunidad no existe.")
        self._enforce_scope(opportunity, actor)

        resolved = self._resolve_ids(data)

        if data.title is not None:
            opportunity.title = data.title
        if data.description is not None:
            opportunity.description = data.description
        if "stage_id" in resolved:
            opportunity.stage_id = resolved["stage_id"]
        if "type_id" in resolved:
            opportunity.type_id = resolved["type_id"]
        if "loss_reason_id" in resolved:
            opportunity.loss_reason_id = resolved["loss_reason_id"]
        if "owner_id" in resolved:
            opportunity.owner_id = resolved["owner_id"]
        if data.estimated_amount is not None:
            opportunity.estimated_amount = data.estimated_amount
        if data.probability is not None:
            opportunity.probability = data.probability
        if data.expected_close_date is not None:
            opportunity.expected_close_date = data.expected_close_date
        if data.actual_close_date is not None:
            opportunity.actual_close_date = data.actual_close_date

        self.repo.flush()
        self.repo.refresh(opportunity)

        if self.audit:
            self.audit.record(
                "opportunity.updated",
                "opportunity",
                opportunity.public_id,
                label=f"Oportunidad: {opportunity.title}",
            )

        return opportunity

    def delete_opportunity(self, public_id: UUID, actor: User) -> None:
        opportunity = self.repo.get_opportunity(public_id)
        if opportunity is None:
            raise NotFoundError("La oportunidad no existe.")
        self._enforce_scope(opportunity, actor)
        self.repo.delete(opportunity)

        if self.audit:
            self.audit.record(
                "opportunity.deleted",
                "opportunity",
                opportunity.public_id,
                label=f"Oportunidad eliminada: {opportunity.title}",
            )
