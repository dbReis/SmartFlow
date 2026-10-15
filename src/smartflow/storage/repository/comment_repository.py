"""Database access for comments. Flushes, never commits: the caller owns the transaction."""

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.comment import Comment
from smartflow.models.notation import Notation

log = structlog.get_logger(__name__)


class CommentRepository:
    """Queries on the comment table, within the caller's session."""

    def __init__(self, session: AsyncSession) -> None:
        """Wrap the request's session."""
        self.session = session

    async def add_comment(self, feedback_id: int, comment: str) -> Comment:
        """Insert a comment and flush, so its id is set.

        Args:
            feedback_id: The feedback it belongs to.
            comment: The text.

        Returns:
            The new comment.
        """
        log.debug("creating_comment", feedback_id=feedback_id)
        comment_obj = Comment(feedback_id=feedback_id, comment=comment)
        self.session.add(comment_obj)
        await self.session.flush()
        log.debug("comment_inserted", comment_id=comment_obj.id)
        return comment_obj

    async def get_comment(self, comment_id: int) -> Comment | None:
        """Return the comment, or None if there is none with that id."""
        return await self.session.get(Comment, comment_id)

    async def list_for_feedback(
        self, feedback_id: int
    ) -> list[tuple[Comment, int, int]]:
        """List a feedback's comments with their score and vote count, in one query.

        One query instead of one per comment (no N+1). The LEFT OUTER JOIN
        keeps comments with no notation: COUNT(notation.id) gives them 0 votes,
        and COALESCE turns their NULL sum into a score of 0.

        Args:
            feedback_id: The feedback whose comments to list.

        Returns:
            ``(comment, score, votes)`` tuples, best score first; ties are
            broken by id, oldest first.
        """
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
        """Move every comment of one feedback to another (used by merge).

        A single bulk UPDATE, without loading the comments.

        Args:
            from_feedback_id: The feedback the comments leave.
            to_feedback_id: The feedback they move to.

        Returns:
            How many comments were moved.
        """
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
