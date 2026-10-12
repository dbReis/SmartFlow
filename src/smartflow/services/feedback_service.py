import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.feedback import Feedback
from smartflow.schemas.feedback import FeedbackCategory, FeedbackCreate
from smartflow.services.errors import CategoryNotFoundError, FeedbackNotFoundError
from smartflow.storage.repository.category_repository import CategoryRepository
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


async def add_to_category(
    session: AsyncSession, feedback_id: int, data: FeedbackCategory
) -> Feedback:
    feedback_repository = FeedbackRepository(session)
    feedback = await feedback_repository.get_feedback(feedback_id)
    if feedback is None:
        log.info("feedback_not_found", feedback_id=feedback_id)
        raise FeedbackNotFoundError(feedback_id)

    if await CategoryRepository(session).get_category(data.category_id) is None:
        log.info("category_not_found", category_id=data.category_id)
        raise CategoryNotFoundError(category_id=data.category_id)

    feedback = await feedback_repository.set_category(feedback, data.category_id)
    log.info(
        "feedback_categorised",
        feedback_id=feedback_id,
        category_id=feedback.category_id,
    )
    return feedback
