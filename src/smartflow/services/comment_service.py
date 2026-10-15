"""Business rules for comments."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.comment import Comment
from smartflow.schemas.comment import CommentCreate
from smartflow.services.feedback_service import get_active_feedback, get_feedback
from smartflow.storage.repository.comment_repository import CommentRepository

log = structlog.get_logger(__name__)


async def create_comment(
    session: AsyncSession, feedback_id: int, data: CommentCreate
) -> Comment:
    """Add a comment to a feedback.

    Args:
        session: The request's session, inside a transaction the caller commits.
        feedback_id: The feedback to comment on.
        data: The validated request body.

    Returns:
        The new comment, with its id assigned.

    Raises:
        FeedbackNotFoundError: If the feedback does not exist.
        FeedbackAlreadyMergedError: If it was merged; merged feedback is read-only.
    """
    await get_active_feedback(session, feedback_id)

    comment = await CommentRepository(session).add_comment(
        feedback_id=feedback_id, comment=data.comment
    )
    log.info("comment_created", comment_id=comment.id, feedback_id=feedback_id)
    return comment


async def list_comments(
    session: AsyncSession, feedback_id: int
) -> list[tuple[Comment, int, int]]:
    """List a feedback's comments with their score and vote count, best first.

    Reading is allowed on merged feedback, so it only checks that it exists.

    Args:
        session: The request's session.
        feedback_id: The feedback whose comments to list.

    Returns:
        ``(comment, score, votes)`` tuples.

    Raises:
        FeedbackNotFoundError: If the feedback does not exist. Without this
            check an unknown id would return an empty list instead of a 404.
    """
    await get_feedback(session, feedback_id)
    return await CommentRepository(session).list_for_feedback(feedback_id)
