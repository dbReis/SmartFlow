import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.feedback import Feedback

log = structlog.get_logger(__name__)


class FeedbackRepository:
    """Database access for feedback. Never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_feedback(self, rating: int, note: str | None = None) -> Feedback:
        feedback = Feedback(rating=rating, note=note)
        self.session.add(feedback)
        # Send the INSERT now (inside the open transaction) so feedback.id is set.
        await self.session.flush()
        log.debug("feedback_inserted", feedback_id=feedback.id)
        return feedback
