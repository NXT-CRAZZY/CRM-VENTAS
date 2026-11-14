from datetime import date
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.modules.interactions.domain.result_pipeline import (
    OPEN_STAGE_ORDER,
    RESULT_TO_STAGE,
    STAGE_PROBABILITY,
)
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.opportunities.repository import OpportunityRepository
from app.modules.opportunities.schemas import OpportunityCreate, OpportunityRead, OpportunityUpdate
from app.modules.prospects.domain.conversion import convert_to_client
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

    def _is_lost_stage(self, stage_id: int) -> bool:
        return stage_id == self.repo.get_catalog_option_id_by_code("pipeline_stage", "CERRADO_PERDIDO")

    @staticmethod
    def _client_status(relationship_type: str | None) -> str:
        return "EXISTENTE" if relationship_type == "CLIENTE" else "NUEVO"

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
        if opportunity.owner_id == user.id or opportunity.prospect.owner_id == user.id:
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
        if resolved.get("type_id") is None and not self._is_lost_stage(resolved["stage_id"]):
            raise AppError("Indica qué se vende.", code="TYPE_REQUIRED")

        opportunity = Opportunity(
            prospect_id=prospect_id,
            stage_id=resolved["stage_id"],
            type_id=resolved.get("type_id"),
            loss_reason_id=(
                resolved.get("loss_reason_id") if self._is_lost_stage(resolved["stage_id"]) else None
            ),
            owner_id=resolved.get("owner_id") or actor.id,
            client_status=self._client_status(self.repo.get_prospect_relationship(prospect_id)),
            title=data.title,
            description=data.description,
            estimated_amount=data.estimated_amount,
            probability=data.probability,
            expected_close_date=data.expected_close_date,
        )
        won_id = self.repo.get_catalog_option_id_by_code("pipeline_stage", "CERRADO_GANADO")
        if resolved["stage_id"] == won_id or self._is_lost_stage(resolved["stage_id"]):
            opportunity.actual_close_date = date.today()
            if opportunity.probability is None:
                opportunity.probability = 100 if resolved["stage_id"] == won_id else 0
        self.repo.add(opportunity)
        if resolved["stage_id"] == won_id:
            self.repo.refresh(opportunity)
            if opportunity.prospect is not None:
                convert_to_client(opportunity.prospect, actor.id)

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
        won_id = self.repo.get_catalog_option_id_by_code("pipeline_stage", "CERRADO_GANADO")
        was_won = opportunity.stage_id == won_id
        old_stage_id = opportunity.stage_id

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
        # El motivo de pérdida solo aplica a oportunidades en Cerrado perdido.
        if not self._is_lost_stage(opportunity.stage_id):
            opportunity.loss_reason_id = None
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

        # Ganar o perder a mano (formulario / Pipeline) deja fecha de cierre y probabilidad coherentes.
        if opportunity.stage_id != old_stage_id:
            self._on_stage_change(opportunity, data, actor, won_id)
        # Si una oportunidad ganada se regresa a otra etapa, su cotizacion aceptada se desbloquea.
        if was_won and opportunity.stage_id != won_id:
            self.repo.reopen_accepted_quotes(opportunity.id)

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

    def _on_stage_change(self, opportunity: Opportunity, data, actor: User, won_id: int | None) -> None:
        lost_id = self.repo.get_catalog_option_id_by_code("pipeline_stage", "CERRADO_PERDIDO")
        if opportunity.stage_id == won_id:
            if data.actual_close_date is None:
                opportunity.actual_close_date = date.today()
            if data.probability is None:
                opportunity.probability = 100
            if opportunity.prospect is not None:
                convert_to_client(opportunity.prospect, actor.id)
        elif opportunity.stage_id == lost_id:
            if data.actual_close_date is None:
                opportunity.actual_close_date = date.today()
            if data.probability is None:
                opportunity.probability = 0
        else:
            # Volvió a una etapa abierta: ya no tiene fecha de cierre.
            if data.actual_close_date is None:
                opportunity.actual_close_date = None

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

    def _pick_open_opportunity(
        self, prospect, opportunity_id: UUID | None, new_opportunity
    ) -> Opportunity | None:
        """Decide a qué oportunidad abierta se aplica la interacción (None = hay que crear una)."""
        if new_opportunity is not None:
            return None
        if opportunity_id is not None:
            chosen = self.repo.get_opportunity(opportunity_id)
            if chosen is None or chosen.prospect_id != prospect.id:
                raise NotFoundError("La oportunidad elegida no existe para este prospecto.")
            if chosen.stage.code in ("CERRADO_GANADO", "CERRADO_PERDIDO"):
                raise AppError("La oportunidad elegida ya está cerrada.", code="OPPORTUNITY_CLOSED")
            return chosen
        open_opps = self.repo.list_open_for_prospect(prospect.id)
        if len(open_opps) > 1:
            raise AppError(
                "El prospecto tiene varias oportunidades abiertas: elige a cuál corresponde esta interacción.",
                code="OPPORTUNITY_REQUIRED",
            )
        return open_opps[0] if open_opps else None

    def sync_from_interaction(
        self,
        prospect,
        result_code: str | None,
        actor: User,
        result_label: str,
        opportunity_id: UUID | None = None,
        new_opportunity=None,
    ) -> tuple[Opportunity | None, str | None]:
        """Aplica el efecto del resultado de una interacción sobre el pipeline del prospecto.

        Devuelve (oportunidad afectada, acción) con acción "created" | "moved" | "closed" | None.
        Una oportunidad abierta solo avanza de etapa; Venta y No interesado la cierran.
        """
        stage_code = RESULT_TO_STAGE.get(result_code or "")
        if stage_code is None or P.OPPORTUNITIES_MANAGE not in actor.permission_codes:
            return None, None

        stage_id = self.repo.get_catalog_option_id_by_code("pipeline_stage", stage_code)
        if stage_id is None:
            return None, None

        open_opp = self._pick_open_opportunity(prospect, opportunity_id, new_opportunity)
        closing = stage_code.startswith("CERRADO_")

        if open_opp is None:
            if stage_code == "CERRADO_PERDIDO" and new_opportunity is None:
                latest = self.repo.get_latest_for_prospect(prospect.id)
                if latest is not None and latest.stage.code == "CERRADO_PERDIDO":
                    return latest, None  # ya figura como perdido: no duplicar
            opportunity = Opportunity(
                prospect_id=prospect.id,
                stage_id=stage_id,
                owner_id=actor.id,
                client_status=self._client_status(prospect.relationship_type),
                type_id=self._catalog(new_opportunity.type_id, "tipo") if new_opportunity else None,
                title=(
                    new_opportunity.title.strip()
                    if new_opportunity
                    else f"{result_label} – {prospect.display_name}"
                )[:200],
                probability=STAGE_PROBABILITY.get(stage_code),
                actual_close_date=date.today() if closing else None,
            )
            self.repo.add(opportunity)
            self.repo.refresh(opportunity)
            action = "created"
        else:
            opportunity = open_opp
            current = opportunity.stage.code
            if not closing and (
                stage_code not in OPEN_STAGE_ORDER
                or current not in OPEN_STAGE_ORDER
                or OPEN_STAGE_ORDER.index(stage_code) <= OPEN_STAGE_ORDER.index(current)
            ):
                return opportunity, None  # no retrocede ni repite etapa
            opportunity.stage_id = stage_id
            opportunity.probability = STAGE_PROBABILITY.get(stage_code, opportunity.probability)
            if closing:
                opportunity.actual_close_date = date.today()
            self.repo.flush()
            self.repo.refresh(opportunity)
            action = "closed" if closing else "moved"

        if stage_code == "CERRADO_GANADO":
            convert_to_client(prospect, actor.id)

        if self.audit:
            self.audit.record(
                "opportunity.created" if action == "created" else "opportunity.updated",
                "opportunity",
                opportunity.public_id,
                label=f"Oportunidad: {opportunity.title}",
                after={"stage": stage_code, "origen": "interaccion"},
            )
        return opportunity, action
