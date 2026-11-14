from datetime import datetime
from uuid import UUID

from app.core.errors import ForbiddenError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.interactions.infrastructure.models import Interaction
from app.modules.opportunities.application.use_cases import OpportunityService
from app.modules.interactions.repository import InteractionRepository
from app.modules.interactions.schemas import FollowUpTask, InteractionCreate, InteractionRead, InteractionUpdate
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.rbac.domain.permissions import P
from app.modules.tasks.application.use_cases import TaskService
from app.modules.tasks.schemas import TaskCreate, TaskUpdate
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams


class InteractionService:
    def __init__(
        self,
        repo: InteractionRepository,
        audit: AuditRecorder | None = None,
        tasks: TaskService | None = None,
        opportunities: OpportunityService | None = None,
    ) -> None:
        self.repo = repo
        self.audit = audit
        self.tasks = tasks
        self.opportunities = opportunities

    def _prospect(self, prospect_public_id: UUID) -> Prospect:
        prospect = self.repo.get_prospect(prospect_public_id)
        if prospect is None:
            raise NotFoundError("El prospecto no existe.")
        return prospect

    def _enforce_read_scope(self, prospect: Prospect, user: User) -> None:
        if P.PROSPECTS_READ_ALL in user.permission_codes:
            return
        if prospect.owner_id != user.id:
            raise ForbiddenError("No tienes acceso a este prospecto.")

    def _enforce_update_scope(self, prospect: Prospect, user: User) -> None:
        if P.PROSPECTS_UPDATE_ALL in user.permission_codes:
            return
        if P.PROSPECTS_UPDATE_OWN in user.permission_codes and prospect.owner_id == user.id:
            return
        raise ForbiddenError("No tienes permiso para modificar este prospecto.")

    def _resolve_ids(self, data: InteractionCreate | InteractionUpdate) -> dict:
        resolved: dict = {}
        if hasattr(data, "channel_id") and data.channel_id:
            resolved["channel_id"] = self._catalog(data.channel_id, "canal")
        if hasattr(data, "result_id") and data.result_id:
            resolved["result_id"] = self._catalog(data.result_id, "resultado")
        if hasattr(data, "interest_level_id") and data.interest_level_id:
            resolved["interest_level_id"] = self._catalog(data.interest_level_id, "nivel de interés")
        if hasattr(data, "contact_id") and data.contact_id:
            resolved["contact_id"] = self._contact(data.contact_id)
        return resolved

    def _catalog(self, public_id: UUID, label: str) -> int:
        internal_id = self.repo.get_catalog_option_id(public_id)
        if internal_id is None:
            raise NotFoundError(f"{label.capitalize()} no encontrado.")
        return internal_id

    def _infer_mode_id(self, channel_internal_id: int) -> int | None:
        """La modalidad se deriva del canal: visita presencial vs. cualquier otro medio remoto."""
        channel_code = self.repo.get_catalog_option_code(channel_internal_id)
        mode_code = "PRESENCIAL" if channel_code == "VISITA" else "REMOTO"
        return self.repo.get_catalog_option_id_by_code("contact_mode", mode_code)

    def _contact(self, public_id: UUID) -> int:
        internal_id = self.repo.get_contact_id(public_id)
        if internal_id is None:
            raise NotFoundError("El contacto no existe.")
        return internal_id

    def _validate_contact_belongs(self, contact_id: int | None, prospect: Prospect) -> None:
        if contact_id is None:
            return
        if not any(c.id == contact_id for c in prospect.contacts):
            raise ForbiddenError("El contacto no pertenece al prospecto.")

    def _refresh_prospect_summary(self, prospect: Prospect) -> None:
        prospect_id = prospect.id
        count = self.repo.count_interactions(prospect_id)
        latest = self.repo.latest_interaction(prospect_id)

        prospect.interaction_count = count
        if latest is not None:
            prospect.last_contact_at = latest.occurred_at
            prospect.last_result_id = latest.result_id
            prospect.interest_level_id = latest.interest_level_id
            if prospect.first_contact_at is None:
                prospect.first_contact_at = latest.occurred_at
        else:
            prospect.last_contact_at = None
            prospect.last_result_id = None
            prospect.interest_level_id = None
            prospect.first_contact_at = None

    def _sync_opportunity(
        self,
        interaction: Interaction,
        prospect: Prospect,
        actor: User,
        opportunity_id: UUID | None = None,
        new_opportunity=None,
    ) -> None:
        """El resultado de la interacción crea/mueve/cierra la oportunidad del prospecto."""
        interaction.opportunity_action = None
        if self.opportunities is None:
            return
        result_code = self.repo.get_catalog_option_code(interaction.result_id)
        result_label = interaction.result.name if interaction.result is not None else (result_code or "")
        opportunity, action = self.opportunities.sync_from_interaction(
            prospect, result_code, actor, result_label, opportunity_id, new_opportunity
        )
        if opportunity is not None:
            interaction.opportunity_id = opportunity.id
            self.repo.refresh_opportunity(interaction)
        interaction.opportunity_action = action

    def _require_task_permission(self, actor: User) -> None:
        if P.TASKS_MANAGE not in actor.permission_codes:
            raise ForbiddenError("No tienes permiso para crear tareas de seguimiento.")

    def _save_follow_up(
        self, interaction: Interaction, prospect: Prospect, data: FollowUpTask, actor: User
    ) -> None:
        """Crea o actualiza la tarea vinculada (próxima acción) reutilizando TaskService."""
        self._require_task_permission(actor)
        fields = data.model_dump()
        existing = interaction.follow_up_task
        if existing is not None:
            self.tasks.update_task(existing.public_id, TaskUpdate(**fields), actor, check_scope=False)
        else:
            fields["assignee_id"] = fields["assignee_id"] or actor.public_id
            self.tasks.create_task(
                TaskCreate(prospect_id=prospect.public_id, **fields), actor, interaction_id=interaction.id
            )

    def _remove_follow_up(self, interaction: Interaction, actor: User, only_pending: bool = False) -> None:
        existing = interaction.follow_up_task
        if existing is None or (only_pending and existing.status != "PENDING"):
            return
        self.tasks.delete_task(existing.public_id, actor, check_scope=False)

    def list_interactions(self, prospect_public_id: UUID, params: PageParams, user: User) -> Page[InteractionRead]:
        prospect = self._prospect(prospect_public_id)
        self._enforce_read_scope(prospect, user)
        items, total = self.repo.list_interactions(prospect_public_id, params)
        return Page(
            items=[InteractionRead.model_validate(i) for i in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def create_interaction(
        self, prospect_public_id: UUID, data: InteractionCreate, actor: User
    ) -> InteractionRead:
        prospect = self._prospect(prospect_public_id)
        self._enforce_read_scope(prospect, actor)

        resolved = self._resolve_ids(data)
        self._validate_contact_belongs(resolved.get("contact_id"), prospect)

        attempt_number = self.repo.count_interactions(prospect.id) + 1
        occurred_at = data.occurred_at or datetime.now()

        interaction = Interaction(
            prospect_id=prospect.id,
            user_id=actor.id,
            contact_id=resolved.get("contact_id"),
            occurred_at=occurred_at,
            channel_id=resolved["channel_id"],
            mode_id=self._infer_mode_id(resolved["channel_id"]),
            result_id=resolved["result_id"],
            interest_level_id=resolved.get("interest_level_id"),
            attempt_number=attempt_number,
            notes=data.notes,
            stage_before=prospect.status,
            stage_after=prospect.status,
        )
        self.repo.add(interaction)
        self._refresh_prospect_summary(prospect)
        self._sync_opportunity(interaction, prospect, actor, data.opportunity_id, data.new_opportunity)

        if data.follow_up_task is not None:
            self._save_follow_up(interaction, prospect, data.follow_up_task, actor)
            self.repo.refresh_follow_up(interaction)

        if self.audit:
            self.audit.record(
                "interaction.created",
                "interaction",
                interaction.public_id,
                label=f"Interacción #{attempt_number} - {prospect.display_name}",
                after={"prospect_id": str(prospect.public_id)},
            )

        return InteractionRead.model_validate(interaction)

    def update_interaction(
        self,
        prospect_public_id: UUID,
        interaction_public_id: UUID,
        data: InteractionUpdate,
        actor: User,
    ) -> InteractionRead:
        prospect = self._prospect(prospect_public_id)
        self._enforce_update_scope(prospect, actor)

        interaction = self.repo.get_interaction(prospect_public_id, interaction_public_id)
        if interaction is None:
            raise NotFoundError("La interacción no existe.")

        resolved = self._resolve_ids(data)
        if "contact_id" in resolved:
            self._validate_contact_belongs(resolved["contact_id"], prospect)
            interaction.contact_id = resolved["contact_id"]

        if data.occurred_at is not None:
            interaction.occurred_at = data.occurred_at
        if "channel_id" in resolved:
            interaction.channel_id = resolved["channel_id"]
            interaction.mode_id = self._infer_mode_id(resolved["channel_id"])
        result_changed = "result_id" in resolved and resolved["result_id"] != interaction.result_id
        if "result_id" in resolved:
            interaction.result_id = resolved["result_id"]
        if "interest_level_id" in resolved:
            interaction.interest_level_id = resolved.get("interest_level_id")
        if data.notes is not None:
            interaction.notes = data.notes

        if data.follow_up_task is not None:
            self._save_follow_up(interaction, prospect, data.follow_up_task, actor)
            self.repo.refresh_follow_up(interaction)
        elif data.remove_follow_up_task and interaction.follow_up_task is not None:
            self._require_task_permission(actor)
            self._remove_follow_up(interaction, actor)
            self.repo.refresh_follow_up(interaction)

        self._refresh_prospect_summary(prospect)
        explicit_choice = data.opportunity_id is not None or data.new_opportunity is not None
        if result_changed or explicit_choice:
            self.repo.refresh_result(interaction)
            # Sin elección explícita, se mantiene la oportunidad que ya tenía ligada la interacción.
            linked = interaction.opportunity
            opportunity_id = data.opportunity_id
            if opportunity_id is None and data.new_opportunity is None and linked is not None:
                opportunity_id = linked.public_id if linked.stage.code not in ("CERRADO_GANADO", "CERRADO_PERDIDO") else None
            self._sync_opportunity(interaction, prospect, actor, opportunity_id, data.new_opportunity)

        if self.audit:
            self.audit.record(
                "interaction.updated",
                "interaction",
                interaction.public_id,
                label=f"Interacción #{interaction.attempt_number} - {prospect.display_name}",
            )

        return InteractionRead.model_validate(interaction)

    def delete_interaction(
        self, prospect_public_id: UUID, interaction_public_id: UUID, actor: User
    ) -> None:
        prospect = self._prospect(prospect_public_id)
        self._enforce_update_scope(prospect, actor)

        interaction = self.repo.get_interaction(prospect_public_id, interaction_public_id)
        if interaction is None:
            raise NotFoundError("La interacción no existe.")

        # La próxima acción pendiente se va con la interacción; las completadas se conservan.
        self._remove_follow_up(interaction, actor, only_pending=True)
        self.repo.delete(interaction)
        self._refresh_prospect_summary(prospect)

        if self.audit:
            self.audit.record(
                "interaction.deleted",
                "interaction",
                interaction.public_id,
                label=f"Interacción #{interaction.attempt_number} - {prospect.display_name}",
            )
