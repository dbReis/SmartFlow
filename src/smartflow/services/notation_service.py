"""Business rules for notations (votes on comments)."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.notation import Notation
from smartflow.schemas.notation import NotationCreate
from smartflow.services.errors import CommentNotFoundError
from smartflow.storage.repository.comment_repository import CommentRepository
from smartflow.storage.repository.notation_repository import NotationRepository

log = structlog.get_logger(__name__)


async def set_notation(
    session: AsyncSession, comment_id: int, user_id: str, data: NotationCreate
) -> Notation:
    """Set the user's notation on a comment: create it, or change their vote.

    Each user has at most one notation per comment. Giving 0 works as
    removing the vote, since it adds nothing to the score.

    Args:
        session: The request's session, inside a transaction the caller commits.
        comment_id: The comment voted on.
        user_id: Who votes.
        data: The validated body with the notation (-1, 0 or +1).

    Returns:
        The user's notation on that comment.

    Raises:
        CommentNotFoundError: If the comment does not exist.
    """
    if await CommentRepository(session).get_comment(comment_id=comment_id) is None:
        log.info("notation_comment_not_found", comment_id=comment_id)
        raise CommentNotFoundError(comment_id=comment_id)

    notation = await NotationRepository(session).upsert_notation(
        comment_id=comment_id, user_id=user_id, notation=data.notation
    )
    log.info("notation_set", notation_id=notation.id, comment_id=comment_id)
    return notation
