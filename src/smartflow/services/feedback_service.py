"""Business rules for feedback: creating, reading, categorising, status and merging.

Merged feedback is read-only: every write goes through get_active_feedback(),
which rejects it.
"""

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
    """Create a feedback. New feedback is open, with no category.

    Args:
        session: The request's session, inside a transaction the caller commits.
        data: The validated request body.

    Returns:
        The new feedback, with its id assigned.
    """
    feedback = await FeedbackRepository(session).add_feedback(
        rating=data.rating, note=data.note
    )
    log.info(
        "feedback_created",
        feedback_id=feedback.id,
        rating=feedback.rating,
        # Log whether there is a note, never the note itself (user text).
        has_note=feedback.note is not None,
    )
    return feedback


async def list_feedback(session: AsyncSession) -> list[tuple[Feedback, int]]:
    """Return the active feedback, newest first, with comment counts.

    Returns:
        ``(feedback, comment_count)`` tuples, at most 100.
    """
    return await FeedbackRepository(session).list_feedback()


async def get_feedback(session: AsyncSession, feedback_id: int) -> Feedback:
    """Return a feedback, merged or not. Use it for reads.

    Raises:
        FeedbackNotFoundError: If it does not exist.
    """
    feedback = await FeedbackRepository(session).get_feedback(feedback_id)
    if feedback is None:
        log.info("feedback_not_found", feedback_id=feedback_id)
        raise FeedbackNotFoundError(feedback_id)
    return feedback


async def get_active_feedback(session: AsyncSession, feedback_id: int) -> Feedback:
    """Return a feedback that can still be changed. Use it before any write.

    Raises:
        FeedbackNotFoundError: If it does not exist.
        FeedbackAlreadyMergedError: If it was merged into another feedback.
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
    """Put a feedback in a category, or take it out of one.

    Args:
        session: The request's session, inside a transaction the caller commits.
        feedback_id: The feedback to categorise.
        data: The validated body; ``category_id=None`` removes the category.

    Returns:
        The updated feedback.

    Raises:
        FeedbackNotFoundError: If the feedback does not exist.
        FeedbackAlreadyMergedError: If it was merged.
        CategoryNotFoundError: If the category does not exist. Checked here so
            the client gets a clear 404 instead of a foreign key error.
    """
    feedback = await get_active_feedback(session, feedback_id)

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
    """Change a feedback's status.

    Any status can follow any other (a closed feedback can be reopened).

    Args:
        session: The request's session, inside a transaction the caller commits.
        feedback_id: The feedback to update.
        data: The validated body with the new status.

    Returns:
        The updated feedback.

    Raises:
        FeedbackNotFoundError: If the feedback does not exist.
        FeedbackAlreadyMergedError: If it was merged.
    """
    feedback = await get_active_feedback(session, feedback_id)
    feedback = await FeedbackRepository(session).update_status(feedback, data.status)
    log.info("feedback_status_updated", feedback_id=feedback_id, status=feedback.status)
    return feedback


async def merge(
    session: AsyncSession, feedback_id: int, data: FeedbackMergeCreate
) -> Feedback:
    """Merge a duplicate feedback (the source) into another one (the target).

    The source's comments move to the target, and the source is marked as
    merged, which hides it from the list and makes it read-only. Feedback that
    had been merged into the source is re-pointed to the target, so no chain
    ever points at a merged feedback. All steps share the caller's transaction:
    if one fails, nothing is changed.

    Args:
        session: The request's session, inside a transaction the caller commits.
        feedback_id: The source, which is merged away.
        data: The validated body with the target id.

    Returns:
        The target feedback.

    Raises:
        CannotMergeIntoItselfError: If source and target are the same.
        FeedbackNotFoundError: If either feedback does not exist.
        FeedbackAlreadyMergedError: If either one was already merged.
    """
    if feedback_id == data.target_id:
        log.info("feedback_merge_into_itself", feedback_id=feedback_id)
        raise CannotMergeIntoItselfError(feedback_id)

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
