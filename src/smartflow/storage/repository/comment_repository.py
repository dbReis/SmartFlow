import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.comment import Comment
from smartflow.models.notation import Notation

log = structlog.get_logger(__name__)


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_comment(self, feedback_id: int, comment: str) -> Comment:
        log.debug("creating_comment", feedback_id=feedback_id)
        comment_obj = Comment(feedback_id=feedback_id, comment=comment)
        self.session.add(comment_obj)
        await self.session.flush()
        log.debug("comment_inserted", comment_id=comment_obj.id)
        return comment_obj

    async def get_comment(self, comment_id: int) -> Comment | None:
        return await self.session.get(Comment, comment_id)

    async def list_for_feedback(
        self, feedback_id: int
    ) -> list[tuple[Comment, int, int]]:
        score = func.coalesce(func.sum(Notation.notation), 0)
        votes = func.count(Notation.id)
        statement = (
            select(Comment, score, votes)
            .outerjoin(Notation, Notation.comment_id == Comment.id)
            .where(Comment.feedback_id == feedback_id)
            .group_by(Comment.id)
            .order_by(score.desc(), Comment.id)
        )
        rows = (await self.session.execute(statement)).all()
        log.debug("comments_listed", feedback_id=feedback_id, count=len(rows))
        return [(comment, score, votes) for comment, score, votes in rows]

    async def move_comments(self, from_feedback_id: int, to_feedback_id: int) -> int:
        result = await self.session.execute(
            update(Comment)
            .where(Comment.feedback_id == from_feedback_id)
            .values(feedback_id=to_feedback_id)
        )
        log.debug(
            "comments_moved",
            from_feedback_id=from_feedback_id,
            to_feedback_id=to_feedback_id,
            count=result.rowcount,
        )
        return result.rowcount
