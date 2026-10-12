import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.comment import Comment
from smartflow.schemas.comment import CommentCreate
from smartflow.services.feedback_service import get_active_feedback
from smartflow.storage.repository.comment_repository import CommentRepository

log = structlog.get_logger(__name__)


async def create_comment(
    session: AsyncSession, feedback_id: int, data: CommentCreate
) -> Comment:
    # Check first, so a missing feedback is a clear 404 instead of a
    # foreign-key violation from the database (which would surface as a 500),
    # and a merged (read-only) feedback is a 409.
    await get_active_feedback(session, feedback_id)

    comment = await CommentRepository(session).add_comment(
        feedback_id=feedback_id, comment=data.comment
    )
    # The comment text is user content: log ids only.
    log.info("comment_created", comment_id=comment.id, feedback_id=feedback_id)
    return comment
