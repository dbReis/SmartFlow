import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.feedback import Feedback
from smartflow.schemas.feedback import FeedbackCreate
from smartflow.storage.repository.feedback_repository import FeedbackRepository

log = structlog.get_logger(__name__)


async def create_feedback(session: AsyncSession, data: FeedbackCreate) -> Feedback:
    feedback = await FeedbackRepository(session).add_feedback(
        rating=data.rating, note=data.note
    )
    log.info(
        "feedback_created",
        feedback_id=feedback.id,
        rating=feedback.rating,
        has_note=feedback.note is not None,
    )
    return feedback
