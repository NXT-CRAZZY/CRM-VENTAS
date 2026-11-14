from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.modules.interactions.domain.result_pipeline import OPEN_STAGE_ORDER, STAGE_PROBABILITY
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.prospects.domain.conversion import convert_to_client
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.quotes.infrastructure.models import Quote, QuoteItem
from app.modules.quotes.repository import QuoteRepository
from app.modules.quotes.schemas import QuoteCreate, QuoteItemCreate, QuoteRead, QuoteStatusChange, QuoteUpdate
from app.modules.rbac.domain.permissions import P
from app.modules.settings.domain.registry import AlertSettings
from app.modules.tasks.infrastructure.models import Task
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams

TAX_RATE = Decimal("0.18")

# Transiciones permitidas. ACCEPTED es final (solo se desbloquea si la oportunidad se regresa en el pipeline).
TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SENT"},
    "SENT": {"ACCEPTED", "REJECTED", "DRAFT"},
    "REJECTED": {"DRAFT"},
    "ACCEPTED": set(),
}
CLOSED_STAGES = ("CERRADO_GANADO", "CERRADO_PERDIDO")


class QuoteService:
    def __init__(
        self,
        repo: QuoteRepository,
        audit: AuditRecorder | None = None,
        settings: AlertSettings | None = None,
    ) -> None:
        self.repo = repo
        self.audit = audit
        self.settings = settings or AlertSettings()

    def _prospect(self, public_id: UUID) -> int:
        internal_id = self.repo.get_prospect_id(public_id)
        if internal_id is None:
            raise NotFoundError("El prospecto no existe.")
        return internal_id

    def _opportunity(self, public_id: UUID | None) -> int | None:
        if public_id is None:
            return None
        internal_id = self.repo.get_opportunity_id(public_id)
        if internal_id is None:
            raise NotFoundError("La oportunidad no existe.")
        return internal_id

    def _product(self, public_id: UUID | None) -> int | None:
        if public_id is None:
            return None
        internal_id = self.repo.get_product_id(public_id)
        if internal_id is None:
            raise NotFoundError("El producto no existe.")
        return internal_id

    def _build_items(self, items: list[QuoteItemCreate]) -> list[QuoteItem]:
        result: list[QuoteItem] = []
        for item in items:
            total = Decimal(str(item.unit_price)) * Decimal(item.quantity)
            result.append(
                QuoteItem(
                    product_id=self._product(item.product_id),
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=total,
                )
            )
        return result

    def _recalculate(self, quote: Quote) -> None:
        subtotal = sum(Decimal(str(i.total)) for i in quote.items)
        tax = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
        quote.subtotal = subtotal
        quote.tax = tax
        quote.total = subtotal + tax

    def _check_opportunity_belongs(self, opportunity_id: int | None, prospect_id: int) -> None:
        if opportunity_id is not None and self.repo.opportunity_prospect_id(opportunity_id) != prospect_id:
            raise NotFoundError("La oportunidad no pertenece a este cliente.")

    def _enforce_scope(self, quote: Quote, user: User) -> None:
        if P.PROSPECTS_READ_ALL in user.permission_codes:
            return
        if quote.prospect.owner_id == user.id:
            return
        raise ForbiddenError("No tienes acceso a esta cotización.")

    def list_quotes(self, filters: dict, params: PageParams, user: User) -> Page[QuoteRead]:
        items, total = self.repo.list_quotes(filters, params, user)
        return Page(
            items=[QuoteRead.model_validate(i) for i in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def create_quote(self, data: QuoteCreate, actor: User) -> Quote:
        prospect_id = self._prospect(data.prospect_id)
        opportunity_id = self._opportunity(data.opportunity_id)
        self._check_opportunity_belongs(opportunity_id, prospect_id)

        quote = Quote(
            prospect_id=prospect_id,
            opportunity_id=opportunity_id,
            status="DRAFT",
            issue_date=data.issue_date,
            expiration_date=data.expiration_date,
            notes=data.notes,
            items=self._build_items(data.items),
        )
        self._recalculate(quote)
        self.repo.add(quote)

        if self.audit:
            self.audit.record(
                "quote.created",
                "quote",
                quote.public_id,
                label=f"Cotización: {quote.prospect.display_name}",
                after={"total": str(quote.total)},
            )

        return quote

    def update_quote(self, public_id: UUID, data: QuoteUpdate, actor: User) -> Quote:
        quote = self.repo.get_quote(public_id)
        if quote is None:
            raise NotFoundError("La cotización no existe.")
        self._enforce_scope(quote, actor)
        if quote.status != "DRAFT":
            raise AppError(
                "La cotización ya fue enviada y está bloqueada. Reábrela a borrador para editarla.",
                code="QUOTE_LOCKED",
            )

        if data.opportunity_id is not None:
            quote.opportunity_id = self._opportunity(data.opportunity_id)
            self._check_opportunity_belongs(quote.opportunity_id, quote.prospect_id)
        if data.issue_date is not None:
            quote.issue_date = data.issue_date
        if data.expiration_date is not None:
            quote.expiration_date = data.expiration_date
        if data.notes is not None:
            quote.notes = data.notes
        if data.items is not None:
            quote.items = self._build_items(data.items)
            self._recalculate(quote)

        self.repo.add(quote)

        if self.audit:
            self.audit.record(
                "quote.updated",
                "quote",
                quote.public_id,
                label=f"Cotización: {quote.prospect.display_name}",
            )

        return quote

    # ---------- cambios de estado ----------

    def _set_stage(self, opportunity, stage_code: str, *, loss_reason_id: int | None = None) -> None:
        stage_id = self.repo.catalog_id_by_code("pipeline_stage", stage_code)
        if stage_id is None:
            return
        opportunity.stage_id = stage_id
        opportunity.probability = STAGE_PROBABILITY.get(stage_code, opportunity.probability)
        opportunity.loss_reason_id = loss_reason_id if stage_code == "CERRADO_PERDIDO" else None
        if stage_code in CLOSED_STAGES:
            opportunity.actual_close_date = date.today()
        self.repo.add_opportunity_refresh(opportunity)

    def _cancel_followups(self, quote_ids: list[int]) -> None:
        for task in self.repo.pending_tasks(quote_ids):
            task.status = "CANCELLED"

    def _on_send(self, quote: Quote, actor: User) -> None:
        if not quote.items or Decimal(str(quote.total)) <= 0:
            raise AppError("Agrega al menos un producto con precio antes de enviar.", code="QUOTE_INCOMPLETE")
        now = datetime.now(UTC)
        quote.sent_at = now
        quote.accepted_at = quote.rejected_at = None
        quote.reject_reason_id = None
        if quote.expiration_date is None:
            quote.expiration_date = max(quote.issue_date, date.today()) + timedelta(
                days=self.settings.quote_validity_days
            )

        # Sin oportunidad ligada: si el cliente tiene una sola abierta, se liga.
        if quote.opportunity_id is None:
            open_opps = self.repo.open_opportunities_of_prospect(quote.prospect_id)
            if len(open_opps) == 1:
                quote.opportunity_id = open_opps[0].id

        if quote.opportunity_id is not None:
            opp = self.repo.get_opportunity(quote.opportunity_id)
            if opp is not None and opp.stage.code not in CLOSED_STAGES:
                if opp.stage.code in OPEN_STAGE_ORDER and OPEN_STAGE_ORDER.index(
                    opp.stage.code
                ) < OPEN_STAGE_ORDER.index("COTIZACION"):
                    self._set_stage(opp, "COTIZACION")
                opp.estimated_amount = quote.total

        self.repo.add_task(
            Task(
                prospect_id=quote.prospect_id,
                opportunity_id=quote.opportunity_id,
                quote_id=quote.id,
                assignee_id=quote.prospect.owner_id or actor.id,
                title=f"Dar seguimiento a la cotización de {quote.prospect.display_name}",
                due_at=now + timedelta(days=self.settings.quote_no_response_days),
                status="PENDING",
            )
        )

    def _on_accept(self, quote: Quote) -> None:
        quote.accepted_at = datetime.now(UTC)
        quote.rejected_at = None
        quote.reject_reason_id = None
        convert_to_client(quote.prospect, quote.prospect.owner_id)
        affected = [quote.id]
        if quote.opportunity_id is not None:
            opp = self.repo.get_opportunity(quote.opportunity_id)
            if opp is not None:
                if opp.stage.code != "CERRADO_GANADO":
                    self._set_stage(opp, "CERRADO_GANADO")
                opp.estimated_amount = quote.total
            # Las demás cotizaciones abiertas de esta oportunidad quedan descartadas.
            for other in self.repo.sibling_quotes(quote.opportunity_id, quote.id):
                if other.status in ("DRAFT", "SENT"):
                    other.status = "REJECTED"
                    other.rejected_at = datetime.now(UTC)
                    affected.append(other.id)
        self._cancel_followups(affected)

    def _on_reject(self, quote: Quote, data: QuoteStatusChange) -> None:
        if data.reject_reason_id is None:
            raise AppError("Indica el motivo del rechazo.", code="REJECT_REASON_REQUIRED")
        reason_id = self.repo.catalog_id_by_public("loss_reason", data.reject_reason_id)
        if reason_id is None:
            raise NotFoundError("El motivo de rechazo no existe.")
        quote.rejected_at = datetime.now(UTC)
        quote.reject_reason_id = reason_id
        self._cancel_followups([quote.id])
        if data.close_opportunity and quote.opportunity_id is not None:
            opp = self.repo.get_opportunity(quote.opportunity_id)
            if opp is not None and opp.stage.code not in CLOSED_STAGES:
                self._set_stage(opp, "CERRADO_PERDIDO", loss_reason_id=reason_id)

    def _on_reopen(self, quote: Quote) -> None:
        quote.sent_at = quote.accepted_at = quote.rejected_at = None
        quote.reject_reason_id = None
        self._cancel_followups([quote.id])

    def change_status(self, public_id: UUID, data: QuoteStatusChange, actor: User) -> Quote:
        quote = self.repo.get_quote(public_id)
        if quote is None:
            raise NotFoundError("La cotización no existe.")
        self._enforce_scope(quote, actor)

        old_status = quote.status
        new_status = data.status
        if new_status not in TRANSITIONS.get(old_status, set()):
            raise AppError(
                f"No se puede pasar una cotización de {old_status} a {new_status}.", code="INVALID_TRANSITION"
            )

        if new_status == "SENT":
            self._on_send(quote, actor)
        elif new_status == "ACCEPTED":
            self._on_accept(quote)
        elif new_status == "REJECTED":
            self._on_reject(quote, data)
        else:
            self._on_reopen(quote)
        quote.status = new_status

        self.repo.add(quote)
        self.repo.add_opportunity_refresh(quote)

        if self.audit:
            self.audit.record(
                "quote.status_changed",
                "quote",
                quote.public_id,
                label=f"Cotización {new_status}: {quote.prospect.display_name}",
                before={"status": old_status},
                after={"status": new_status},
            )

        return quote

    def delete_quote(self, public_id: UUID, actor: User) -> None:
        quote = self.repo.get_quote(public_id)
        if quote is None:
            raise NotFoundError("La cotización no existe.")
        self._enforce_scope(quote, actor)
        self.repo.delete(quote)

        if self.audit:
            self.audit.record(
                "quote.deleted",
                "quote",
                quote.public_id,
                label=f"Cotización eliminada: {quote.prospect.display_name}",
            )
