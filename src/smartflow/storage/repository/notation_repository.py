"""Database access for notations."""

import structlog
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.notation import Notation

log = structlog.get_logger(__name__)


class NotationRepository:
    """Queries on the notation table, within the caller's session."""

    def __init__(self, session: AsyncSession) -> None:
        """Wrap the request's session."""
        self.session = session

    async def upsert_notation(
        self, comment_id: int, user_id: str, notation: int
    ) -> Notation:
        """Insert the user's notation on a comment, or replace the one they gave.

        A single INSERT ... ON CONFLICT DO UPDATE on the (comment_id, user_id)
        unique key. The database decides atomically, so two simultaneous votes
        from the same user can't create two rows (a SELECT-then-INSERT could).

        Args:
            comment_id: The comment voted on.
            user_id: Who votes.
            notation: -1, 0 or +1.

        Returns:
            The user's notation on that comment, as now stored.
        """
        log.debug("upserting_vote", comment_id=comment_id, notation=notation)
        statement = insert(Notation).values(
            comment_id=comment_id, user_id=user_id, notation=notation
        )
        statement = statement.on_conflict_do_update(
            index_elements=[Notation.comment_id, Notation.user_id],
            set_={"notation": statement.excluded.notation},
        ).returning(Notation)
        notation_obj = await self.session.scalar(
            statement, execution_options={"populate_existing": True}
        )
        log.debug("vote_upserted", notation_id=notation_obj.id)
        return notation_obj
