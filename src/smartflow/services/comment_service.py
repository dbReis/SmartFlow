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
    await get_active_feedback(session, feedback_id)

    comment = await CommentRepository(session).add_comment(
        feedback_id=feedback_id, comment=data.comment
    )
    log.info("comment_created", comment_id=comment.id, feedback_id=feedback_id)
    return comment


async def list_comments(
    session: AsyncSession, feedback_id: int
) -> list[tuple[Comment, int, int]]:
    await get_feedback(session, feedback_id)
    return await CommentRepository(session).list_for_feedback(feedback_id)
