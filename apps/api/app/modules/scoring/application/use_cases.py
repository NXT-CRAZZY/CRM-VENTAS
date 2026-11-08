from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalogs.infrastructure.models import CatalogOption
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.quotes.infrastructure.models import Quote


class ScoreCalculator:
    def __init__(self, session: Session) -> None:
        self.s = session

    def recalculate(self, prospect: Prospect) -> None:
        score = Decimal("0")
        breakdown: dict[str, float] = {}

        # Interés del prospecto (peso del catálogo)
        if prospect.interest_level_id:
            interest = self.s.get(CatalogOption, prospect.interest_level_id)
            if interest and interest.weight:
                w = float(interest.weight)
                score += Decimal(str(w))
                breakdown["interest_level"] = w

        # Prioridad del prospecto
        if prospect.priority_id:
            priority = self.s.get(CatalogOption, prospect.priority_id)
            if priority and priority.weight:
                w = float(priority.weight) * 2  # la prioridad pesa el doble
                score += Decimal(str(w))
                breakdown["priority"] = w

        # Recencia del último contacto (más reciente, más puntos)
        now = datetime.now(UTC)
        if prospect.last_contact_at:
            days = (now - prospect.last_contact_at).days
            if days <= 2:
                recency = 20
            elif days <= 7:
                recency = 15
            elif days <= 14:
                recency = 10
            elif days <= 30:
                recency = 5
            else:
                recency = 0
            score += Decimal(recency)
            breakdown["recency"] = recency

        # Actividad: interacciones recientes
        interactions = prospect.interaction_count or 0
        activity = min(interactions * 3, 15)
        score += Decimal(activity)
        breakdown["activity"] = activity

        # Pipeline: cotizaciones u oportunidades activas
        quote_count = self.s.scalar(
            select(func.count(Quote.id)).where(  # type: ignore[name-defined]
                Quote.prospect_id == prospect.id,
                Quote.deleted_at.is_(None),
                Quote.status.in_(["DRAFT", "SENT"]),
            )
        ) or 0
        pipeline = min(int(quote_count) * 5, 15)
        score += Decimal(pipeline)
        breakdown["pipeline"] = pipeline

        # Cliente convertido
        if prospect.relationship_type == "CLIENTE":
            score += Decimal(25)
            breakdown["client"] = 25

        # Penalización por estar estancado sin contacto
        if prospect.last_contact_at:
            days = (now - prospect.last_contact_at).days
            if days > 30:
                penalty = -10
                score += Decimal(penalty)
                breakdown["stalled_penalty"] = penalty

        score = max(Decimal("0"), min(score, Decimal("100")))
        prospect.score = score.quantize(Decimal("0.01"))
        prospect.score_breakdown = breakdown
        self.s.add(prospect)

    def recalculate_all(self) -> int:
        prospects = self.s.scalars(select(Prospect).where(Prospect.deleted_at.is_(None))).all()
        for p in prospects:
            self.recalculate(p)
        self.s.flush()
        return len(prospects)
