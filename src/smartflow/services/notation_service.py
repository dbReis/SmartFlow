"""Business rules for notations (votes on comments)."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.notation import Notation
from smartflow.schemas.notation import NotationCreate
from smartflow.services.errors import CommentNotFoundError
from smartflow.storage.repository.comment_repository import CommentRepository
from smartflow.storage.repository.notation_repository import NotationRepository

log = structlog.get_logger(__name__)


async def create_notation(
    session: AsyncSession, comment_id: int, data: NotationCreate
) -> Notation:
    """Record a notation on a comment.

    Args:
        session: The request's session, inside a transaction the caller commits.
        comment_id: The comment voted on.
        data: The validated body with the notation (-1, 0 or +1).

    Returns:
        The new notation, with its id assigned.

    Raises:
        CommentNotFoundError: If the comment does not exist.
    """
    if await CommentRepository(session).get_comment(comment_id=comment_id) is None:
        log.info("notation_comment_not_found", comment_id=comment_id)
        raise CommentNotFoundError(comment_id=comment_id)

    notation = await NotationRepository(session).add_notation(
        comment_id=comment_id, notation=data.notation
    )
    log.info("notation_created", notation_id=notation.id, comment_id=comment_id)
    return notation
