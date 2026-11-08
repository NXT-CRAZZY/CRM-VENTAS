from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.rbac.domain.permissions import P
from app.modules.scoring.application.use_cases import ScoreCalculator

router = APIRouter(tags=["Scoring"], prefix="/scoring")


@router.post("/recalculate-all", response_model=int, dependencies=[Depends(require(P.DASHBOARD_MANAGEMENT))])
def recalculate_all(db: DbSession) -> int:
    return ScoreCalculator(db).recalculate_all()


@router.post(
    "/prospects/{prospect_id}/recalculate",
    response_model=dict,
    dependencies=[Depends(require(P.PROSPECTS_READ_OWN))],
)
def recalculate_prospect(prospect_id: UUID, db: DbSession, user: CurrentUser) -> dict:
    from app.core.errors import ForbiddenError, NotFoundError

    prospect = db.scalar(select(Prospect).where(Prospect.public_id == prospect_id))
    if prospect is None:
        raise NotFoundError("El prospecto no existe.")
    if P.PROSPECTS_READ_ALL not in user.permission_codes and prospect.owner_id != user.id:
        raise ForbiddenError("No tienes acceso a este prospecto.")
    ScoreCalculator(db).recalculate(prospect)
    return {"score": str(prospect.score), "breakdown": prospect.score_breakdown}
