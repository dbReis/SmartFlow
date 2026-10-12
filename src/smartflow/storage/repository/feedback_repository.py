import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.feedback import Feedback

log = structlog.get_logger(__name__)


class FeedbackRepository:
    """Database access for feedback. Never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_feedback(self, rating: int, note: str | None = None) -> Feedback:
        log.debug("creating_feedback")
        feedback = Feedback(rating=rating, note=note)
        self.session.add(feedback)
        # Send the INSERT now (inside the open transaction) so feedback.id is set.
        await self.session.flush()
        log.debug("feedback_inserted", feedback_id=feedback.id)
        return feedback

    async def get_feedback(self, feedback_id: int) -> Feedback | None:
        return await self.session.get(Feedback, feedback_id)

    async def set_category(
        self, feedback: Feedback, category_id: int | None
    ) -> Feedback:
        feedback.category_id = category_id
        await self.session.flush()
        log.debug(
            "feedback_category_set", feedback_id=feedback.id, category_id=category_id
        )
        return feedback

    async def update_status(self, feedback: Feedback, status: str) -> Feedback:
        feedback.status = status
        await self.session.flush()
        log.debug("feedback_status_set", feedback_id=feedback.id, status=status)
        return feedback

    async def merge(self, feedback: Feedback, target_id: int) -> Feedback:
        """Mark a feedback as merged into another one."""
        feedback.merged_into_id = target_id
        await self.session.flush()
        log.debug(
            "feedback_marked_merged", feedback_id=feedback.id, target_id=target_id
        )
        return feedback

    async def repoint_merged(self, from_feedback_id: int, to_feedback_id: int) -> None:
        """Feedback merged into `from` now points to `to`, so pointers never chain."""
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
