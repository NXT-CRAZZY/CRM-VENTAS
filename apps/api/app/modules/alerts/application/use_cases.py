from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.alerts.infrastructure.models import Alert
from app.modules.alerts.schemas import AlertFilters
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.quotes.infrastructure.models import Quote
from app.modules.rbac.domain.permissions import P
from app.modules.settings.application.use_cases import SettingsService
from app.modules.settings.domain.registry import AlertSettings
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams


class AlertService:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.settings = cast(AlertSettings, SettingsService(session).get("alerts"))

    def _active_prospect_filter(self, user: User):
        base = (Prospect.deleted_at.is_(None), Prospect.status != "DESCARTADO")
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            return (*base, Prospect.owner_id == user.id)
        return base

    def generate_for_user(self, user: User) -> int:
        count = 0
        count += self._generate_no_first_contact(user)
        count += self._generate_no_followup(user)
        count += self._generate_quote_expiring(user)
        count += self._generate_quote_no_response(user)
        count += self._generate_stalled(user)
        count += self._generate_high_value(user)
        self.s.flush()
        return count

    def _exists(self, user_id: int, alert_type: str, entity_type: str | None, entity_id: str | None) -> bool:
        stmt = select(Alert.id).where(
            Alert.user_id == user_id,
            Alert.alert_type == alert_type,
            Alert.entity_type == entity_type,
            Alert.entity_id == entity_id,
            Alert.dismissed_at.is_(None),
        )
        return self.s.scalar(stmt) is not None

    def _create(
        self,
        user_id: int,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        prospect_id: int | None,
        entity_type: str | None,
        entity_id: str | None,
    ) -> bool:
        if self._exists(user_id, alert_type, entity_type, entity_id):
            return False
        self.s.add(
            Alert(
                user_id=user_id,
                prospect_id=prospect_id,
                alert_type=alert_type,
                severity=severity,
                status="UNREAD",
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )
        return True

    def _generate_no_first_contact(self, user: User) -> int:
        since = datetime.now(UTC) - timedelta(hours=self.settings.uncontacted_hours)
        stmt = select(Prospect).where(
            Prospect.created_at < since,
            Prospect.interaction_count == 0,
            Prospect.relationship_type == "PROSPECTO",
            *self._active_prospect_filter(user),
        )
        count = 0
        for p in self.s.scalars(stmt):
            if self._create(
                user.id,
                "NO_FIRST_CONTACT",
                "HIGH",
                f"{p.display_name}: sin primer contacto",
                (
                    f"El prospecto fue creado hace más de {self.settings.uncontacted_hours} "
                    "horas y aún no tiene interacciones."
                ),
                p.id,
                "prospect",
                str(p.public_id),
            ):
                count += 1
        return count

    def _generate_no_followup(self, user: User) -> int:
        since = datetime.now(UTC) - timedelta(days=self.settings.no_followup_days)
        stmt = select(Prospect).where(
            Prospect.last_contact_at.is_not(None),
            Prospect.last_contact_at < since,
            Prospect.relationship_type == "PROSPECTO",
            *self._active_prospect_filter(user),
        )
        count = 0
        for p in self.s.scalars(stmt):
            if self._create(
                user.id,
                "NO_FOLLOWUP",
                "MEDIUM",
                f"{p.display_name}: sin seguimiento",
                f"Último contacto hace más de {self.settings.no_followup_days} días.",
                p.id,
                "prospect",
                str(p.public_id),
            ):
                count += 1
        return count

    def _generate_quote_expiring(self, user: User) -> int:
        deadline = date.today() + timedelta(days=self.settings.quote_expiring_days)
        stmt = select(Quote).where(
            Quote.deleted_at.is_(None),
            Quote.status == "SENT",
            Quote.expiration_date.is_not(None),
            Quote.expiration_date <= deadline,
            Quote.expiration_date >= date.today(),
        )
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            stmt = stmt.where(Quote.prospect.has(Prospect.owner_id == user.id))
        count = 0
        for q in self.s.scalars(stmt).unique().all():
            if self._create(
                user.id,
                "QUOTE_EXPIRING",
                "HIGH",
                f"Cotización por vencer: {q.prospect.display_name}",
                f"La cotización vence el {cast(date, q.expiration_date).isoformat()}.",
                q.prospect_id,
                "quote",
                str(q.public_id),
            ):
                count += 1
        return count

    def _generate_quote_no_response(self, user: User) -> int:
        since = datetime.now(UTC) - timedelta(days=self.settings.quote_no_response_days)
        stmt = select(Quote).where(
            Quote.deleted_at.is_(None),
            Quote.status == "SENT",
            Quote.updated_at < since,
        )
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            stmt = stmt.where(Quote.prospect.has(Prospect.owner_id == user.id))
        count = 0
        for q in self.s.scalars(stmt).unique().all():
            if self._create(
                user.id,
                "QUOTE_NO_RESPONSE",
                "MEDIUM",
                f"Cotización sin respuesta: {q.prospect.display_name}",
                f"La cotización fue enviada hace más de {self.settings.quote_no_response_days} días sin respuesta.",
                q.prospect_id,
                "quote",
                str(q.public_id),
            ):
                count += 1
        return count

    def _generate_stalled(self, user: User) -> int:
        stmt = select(Prospect).where(
            Prospect.interaction_count >= self.settings.max_attempts,
            Prospect.relationship_type == "PROSPECTO",
            *self._active_prospect_filter(user),
        )
        count = 0
        for p in self.s.scalars(stmt):
            if self._create(
                user.id,
                "STALLED",
                "LOW",
                f"{p.display_name}: prospecto estancado",
                f"Tiene {p.interaction_count} intentos de contacto sin convertirse en cliente.",
                p.id,
                "prospect",
                str(p.public_id),
            ):
                count += 1
        return count

    def _generate_high_value(self, user: User) -> int:
        stmt = select(Opportunity).where(
            Opportunity.deleted_at.is_(None),
            Opportunity.estimated_amount >= Decimal(self.settings.high_value_amount),
        )
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            stmt = stmt.where(Opportunity.prospect.has(Prospect.owner_id == user.id))
        count = 0
        for o in self.s.scalars(stmt):
            if self._create(
                user.id,
                "HIGH_VALUE",
                "CRITICAL",
                f"Oportunidad de alto valor: {o.prospect.display_name}",
                f"Monto estimado S/ {o.estimated_amount}.",
                o.prospect_id,
                "opportunity",
                str(o.public_id),
            ):
                count += 1
        return count

    def list_alerts(self, filters: AlertFilters, params: PageParams, user: User) -> Page[Any]:
        stmt = select(Alert).where(Alert.user_id == user.id)
        if filters.status == "DISMISSED":
            stmt = stmt.where(Alert.status == "DISMISSED")
        else:
            stmt = stmt.where(Alert.dismissed_at.is_(None))
            if filters.status:
                stmt = stmt.where(Alert.status == filters.status)
        if filters.severity:
            stmt = stmt.where(Alert.severity == filters.severity)
        stmt = stmt.order_by(Alert.created_at.desc())
        items, total = self._paginate(stmt, params)
        return Page(items=items, total=total, page=params.page, page_size=params.page_size)

    def _paginate(self, stmt, params: PageParams) -> tuple[list[Alert], int]:
        from app.shared.pagination import paginate

        return paginate(self.s, stmt, params)

    def mark_read(self, alert_id: UUID, user: User) -> Alert:
        alert = self.s.scalar(select(Alert).where(Alert.public_id == alert_id, Alert.user_id == user.id))
        if alert is None:
            from app.core.errors import NotFoundError

            raise NotFoundError("La alerta no existe.")
        alert.status = "READ"
        alert.read_at = datetime.now(UTC)
        self.s.add(alert)
        return alert

    def dismiss(self, alert_id: UUID, user: User) -> Alert:
        alert = self.s.scalar(select(Alert).where(Alert.public_id == alert_id, Alert.user_id == user.id))
        if alert is None:
            from app.core.errors import NotFoundError

            raise NotFoundError("La alerta no existe.")
        alert.status = "DISMISSED"
        alert.dismissed_at = datetime.now(UTC)
        self.s.add(alert)
        return alert

    def unread_count(self, user: User) -> int:
        return self.s.scalar(
            select(func.count(Alert.id)).where(
                Alert.user_id == user.id, Alert.status == "UNREAD", Alert.dismissed_at.is_(None)
            )
        ) or 0
