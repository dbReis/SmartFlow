"""Database access for feedback. Flushes, never commits: the caller owns the transaction."""

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.comment import Comment
from smartflow.models.feedback import Feedback

log = structlog.get_logger(__name__)

LIST_LIMIT = 100
"""Most feedback list_feedback() returns. A safety cap until pagination is added."""


class FeedbackRepository:
    """Queries on the feedback table, within the caller's session."""

    def __init__(self, session: AsyncSession) -> None:
        """Wrap the request's session."""
        self.session = session

    async def add_feedback(self, rating: int, note: str | None = None) -> Feedback:
        """Insert a feedback and flush, so its id and default status are set.

        Args:
            rating: 1 to 5.
            note: Optional free text.

        Returns:
            The new feedback.
        """
        log.debug("creating_feedback")
        feedback = Feedback(rating=rating, note=note)
        self.session.add(feedback)
        await self.session.flush()
        log.debug("feedback_inserted", feedback_id=feedback.id)
        return feedback

    async def get_feedback(self, feedback_id: int) -> Feedback | None:
        """Return the feedback, or None if there is none with that id."""
        return await self.session.get(Feedback, feedback_id)

    async def list_feedback(self) -> list[tuple[Feedback, int]]:
        """List active feedback with their comment count, in one query.

        LEFT OUTER JOIN so feedback without comments is kept; COUNT(comment.id)
        (not COUNT(*)) gives them 0 instead of 1. Merged feedback is left out.

        Returns:
            ``(feedback, comment_count)`` tuples, newest first, at most LIST_LIMIT.
        """
        comment_count = func.count(Comment.id)
        statement = (
            select(Feedback, comment_count)
            .outerjoin(Comment, Comment.feedback_id == Feedback.id)
            .where(Feedback.merged_into_id.is_(None))
            .group_by(Feedback.id)
            .order_by(Feedback.id.desc())
            .limit(LIST_LIMIT)
        )
        rows = (await self.session.execute(statement)).all()
        log.debug("feedback_listed", count=len(rows))
        return [(feedback, count) for feedback, count in rows]

    async def set_category(
        self, feedback: Feedback, category_id: int | None
    ) -> Feedback:
        """Set (or clear, with None) the feedback's category and flush.

        Returns:
            The same feedback, updated.
        """
        feedback.category_id = category_id
        await self.session.flush()
        log.debug(
            "feedback_category_set", feedback_id=feedback.id, category_id=category_id
        )
        return feedback

    async def update_status(self, feedback: Feedback, status: str) -> Feedback:
        """Set the feedback's status and flush.

        Returns:
            The same feedback, updated.
        """
        feedback.status = status
        await self.session.flush()
        log.debug("feedback_status_set", feedback_id=feedback.id, status=status)
        return feedback

    async def merge(self, feedback: Feedback, target_id: int) -> Feedback:
        """Mark the feedback as merged into ``target_id`` and flush.

        Returns:
            The same feedback, now read-only.
        """
        feedback.merged_into_id = target_id
        await self.session.flush()
        log.debug(
            "feedback_marked_merged", feedback_id=feedback.id, target_id=target_id
        )
        return feedback

    async def repoint_merged(self, from_feedback_id: int, to_feedback_id: int) -> None:
        """Re-point feedback merged into one feedback to another (used by merge).

        If B was merged into A and A is now merged into C, B must point to C,
        not to A, so following ``merged_into_id`` takes one step, never a chain.

        Args:
            from_feedback_id: The feedback being merged away.
            to_feedback_id: The merge target.
        """
        result = await self.session.execute(
            update(Feedback)
            .where(Feedback.merged_into_id == from_feedback_id)
            .values(merged_into_id=to_feedback_id)
        )
        log.debug(
            "merged_feedback_repointed",
            from_feedback_id=from_feedback_id,
            to_feedback_id=to_feedback_id,
            count=result.rowcount,
        )
