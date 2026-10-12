import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.feedback import Feedback
from smartflow.schemas.feedback import (
    FeedbackCategoryCreate,
    FeedbackCreate,
    FeedbackMergeCreate,
    FeedbackStatusCreate,
)
from smartflow.services.errors import (
    CannotMergeIntoItselfError,
    CategoryNotFoundError,
    FeedbackAlreadyMergedError,
    FeedbackNotFoundError,
)
from smartflow.storage.repository.category_repository import CategoryRepository
from smartflow.storage.repository.comment_repository import CommentRepository
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


async def get_active_feedback(session: AsyncSession, feedback_id: int) -> Feedback:
    """Load a feedback that can still be changed.

    Raises FeedbackNotFoundError if it doesn't exist, and FeedbackAlreadyMergedError
    if it was merged into another feedback (merged feedback is read-only).
    """
    feedback = await FeedbackRepository(session).get_feedback(feedback_id)
    if feedback is None:
        log.info("feedback_not_found", feedback_id=feedback_id)
        raise FeedbackNotFoundError(feedback_id)
    if feedback.merged_into_id is not None:
        log.info(
            "feedback_already_merged",
            feedback_id=feedback_id,
            merged_into_id=feedback.merged_into_id,
        )
        raise FeedbackAlreadyMergedError(feedback_id)
    return feedback


async def add_to_category(
    session: AsyncSession, feedback_id: int, data: FeedbackCategoryCreate
) -> Feedback:
    feedback = await get_active_feedback(session, feedback_id)

    # None removes the feedback from its category: nothing to look up.
    category_id = data.category_id
    if (
        category_id is not None
        and await CategoryRepository(session).get_category(category_id) is None
    ):
        log.info("category_not_found", category_id=category_id)
        raise CategoryNotFoundError(category_id)

    feedback = await FeedbackRepository(session).set_category(
        feedback, data.category_id
    )
    log.info(
        "feedback_categorised",
        feedback_id=feedback_id,
        category_id=feedback.category_id,
    )
    return feedback


async def update_status(
    session: AsyncSession, feedback_id: int, data: FeedbackStatusCreate
) -> Feedback:
    feedback = await get_active_feedback(session, feedback_id)
    feedback = await FeedbackRepository(session).update_status(feedback, data.status)
    log.info("feedback_status_updated", feedback_id=feedback_id, status=feedback.status)
    return feedback


async def merge(
    session: AsyncSession, feedback_id: int, data: FeedbackMergeCreate
) -> Feedback:
    """Merge feedback `feedback_id` (source) into `data.target_id` (target).

    The target receives all of the source's comments (and, through them, their
    notations). The source stays, marked as merged, as a read-only record.
    Everything happens in the caller's transaction: all or nothing.
    """
    if feedback_id == data.target_id:
        log.info("feedback_merge_into_itself", feedback_id=feedback_id)
        raise CannotMergeIntoItselfError(feedback_id)

    # Both must exist and still be active: no chains, no cycles.
    source = await get_active_feedback(session, feedback_id)
    target = await get_active_feedback(session, data.target_id)

    feedback_repository = FeedbackRepository(session)
    moved = await CommentRepository(session).move_comments(feedback_id, data.target_id)
    await feedback_repository.repoint_merged(feedback_id, data.target_id)
    await feedback_repository.merge(source, target_id=data.target_id)

    log.info(
        "feedback_merged",
        source_id=feedback_id,
        target_id=data.target_id,
        comments_moved=moved,
    )
    return target
