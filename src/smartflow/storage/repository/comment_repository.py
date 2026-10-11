import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.comment import Comment

log = structlog.get_logger(__name__)


class CommentRepository:
    """Database access for comments. Never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_comment(self, feedback_id: int, comment: str) -> Comment:
        log.debug("creating_comment", feedback_id=feedback_id)
        comment_obj = Comment(feedback_id=feedback_id, comment=comment)
        self.session.add(comment_obj)
        await self.session.flush()
        log.debug("comment_inserted", comment_id=comment_obj.id)
        return comment_obj
