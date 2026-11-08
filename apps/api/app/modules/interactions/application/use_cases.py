from datetime import datetime
from uuid import UUID

from app.core.errors import ForbiddenError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.interactions.infrastructure.models import Interaction
from app.modules.interactions.repository import InteractionRepository
from app.modules.interactions.schemas import InteractionCreate, InteractionRead, InteractionUpdate
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.rbac.domain.permissions import P
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams


class InteractionService:
    def __init__(self, repo: InteractionRepository, audit: AuditRecorder | None = None) -> None:
        self.repo = repo
        self.audit = audit

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
        if hasattr(data, "mode_id") and data.mode_id:
            resolved["mode_id"] = self._catalog(data.mode_id, "modalidad")
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
            prospect.next_action_at = latest.next_action_at
            prospect.next_action_desc = latest.next_action_desc
            if prospect.first_contact_at is None:
                prospect.first_contact_at = latest.occurred_at
        else:
            prospect.last_contact_at = None
            prospect.last_result_id = None
            prospect.interest_level_id = None
            prospect.next_action_at = None
            prospect.next_action_desc = None
            prospect.first_contact_at = None

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
            mode_id=resolved.get("mode_id"),
            result_id=resolved["result_id"],
            interest_level_id=resolved.get("interest_level_id"),
            attempt_number=attempt_number,
            notes=data.notes,
            next_action_desc=data.next_action_desc,
            next_action_at=data.next_action_at,
            stage_before=prospect.status,
            stage_after=prospect.status,
        )
        self.repo.add(interaction)
        self._refresh_prospect_summary(prospect)

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
        if "mode_id" in resolved:
            interaction.mode_id = resolved.get("mode_id")
        if "result_id" in resolved:
            interaction.result_id = resolved["result_id"]
        if "interest_level_id" in resolved:
            interaction.interest_level_id = resolved.get("interest_level_id")
        if data.notes is not None:
            interaction.notes = data.notes
        if data.next_action_desc is not None:
            interaction.next_action_desc = data.next_action_desc
        if data.next_action_at is not None:
            interaction.next_action_at = data.next_action_at

        self._refresh_prospect_summary(prospect)

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

        self.repo.delete(interaction)
        self._refresh_prospect_summary(prospect)

        if self.audit:
            self.audit.record(
                "interaction.deleted",
                "interaction",
                interaction.public_id,
                label=f"Interacción #{interaction.attempt_number} - {prospect.display_name}",
            )
