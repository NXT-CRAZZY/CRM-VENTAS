from decimal import Decimal
from uuid import UUID

from app.core.errors import ForbiddenError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.quotes.infrastructure.models import Quote, QuoteItem
from app.modules.quotes.repository import QuoteRepository
from app.modules.quotes.schemas import QuoteCreate, QuoteItemCreate, QuoteRead, QuoteStatusChange, QuoteUpdate
from app.modules.rbac.domain.permissions import P
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams

TAX_RATE = Decimal("0.18")


class QuoteService:
    def __init__(self, repo: QuoteRepository, audit: AuditRecorder | None = None) -> None:
        self.repo = repo
        self.audit = audit

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

        if data.opportunity_id is not None:
            quote.opportunity_id = self._opportunity(data.opportunity_id)
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

    def change_status(self, public_id: UUID, data: QuoteStatusChange, actor: User) -> Quote:
        quote = self.repo.get_quote(public_id)
        if quote is None:
            raise NotFoundError("La cotización no existe.")
        self._enforce_scope(quote, actor)

        old_status = quote.status
        quote.status = data.status

        if data.status == "ACCEPTED" and quote.prospect.relationship_type != "CLIENTE":
            quote.prospect.relationship_type = "CLIENTE"

        self.repo.add(quote)

        if self.audit:
            self.audit.record(
                "quote.status_changed",
                "quote",
                quote.public_id,
                label=f"Cotización {data.status}: {quote.prospect.display_name}",
                before={"status": old_status},
                after={"status": data.status},
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
