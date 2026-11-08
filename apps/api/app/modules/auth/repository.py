from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import RefreshToken


class RefreshTokenRepository(Protocol):
    def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...
    def add(self, token: RefreshToken) -> None: ...
    def revoke_family(self, family_id: UUID) -> None: ...
    def purge_expired(self, before: datetime) -> int: ...


class SqlRefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.s.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def add(self, token: RefreshToken) -> None:
        self.s.add(token)
        self.s.flush()

    def revoke_family(self, family_id: UUID) -> None:
        self.s.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )

    def purge_expired(self, before: datetime) -> int:
        result = self.s.execute(delete(RefreshToken).where(RefreshToken.expires_at < before))
        return result.rowcount or 0
