"""Database access for notations."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.notation import Notation

log = structlog.get_logger(__name__)


class NotationRepository:
    """Queries on the notation table, within the caller's session."""

    def __init__(self, session: AsyncSession) -> None:
        """Wrap the request's session."""
        self.session = session

    async def add_notation(self, comment_id: int, notation: int) -> Notation:
        """Insert a notation and flush, so its id is set.

        Args:
            comment_id: The comment voted on.
            notation: -1, 0 or +1.

        Returns:
            The new notation.
        """
        log.debug("creating_vote", comment_id=comment_id, notation=notation)
        notation_obj = Notation(comment_id=comment_id, notation=notation)
        self.session.add(notation_obj)
        await self.session.flush()
        log.debug("vote_inserted", notation_id=notation_obj.id)
        return notation_obj
