import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.comment import Comment
from smartflow.schemas.comment import CommentCreate
from smartflow.services.errors import FeedbackNotFoundError
from smartflow.storage.repository.comment_repository import CommentRepository
from smartflow.storage.repository.feedback_repository import FeedbackRepository

log = structlog.get_logger(__name__)


async def create_comment(
    session: AsyncSession, feedback_id: int, data: CommentCreate
) -> Comment:
    # Check first, so a missing feedback is a clear 404 instead of a
    # foreign-key violation from the database (which would surface as a 500).
    if await FeedbackRepository(session).get_feedback(feedback_id) is None:
        log.info("feedback_not_found", feedback_id=feedback_id)
        raise FeedbackNotFoundError(feedback_id)

    comment = await CommentRepository(session).add_comment(
        feedback_id=feedback_id, comment=data.comment
    )
    # The comment text is user content: log ids only.
    log.info("comment_created", comment_id=comment.id, feedback_id=feedback_id)
    return comment
