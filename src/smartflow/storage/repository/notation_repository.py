import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.notation import Notation

log = structlog.get_logger(__name__)


class NotationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_notation(self, comment_id: int, notation: int) -> Notation:
        log.debug("creating_vote", comment_id=comment_id, notation=notation)
        notation_obj = Notation(comment_id=comment_id, notation=notation)
        self.session.add(notation_obj)
        await self.session.flush()
        log.debug("vote_inserted", notation_id=notation_obj.id)
        return notation_obj
