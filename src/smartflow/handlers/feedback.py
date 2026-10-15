"""Feedback endpoints: the public ones and the PM triage ones.

Each handler only translates HTTP to service calls and back: it parses the
body, opens the session, and turns domain errors into status codes.
"""

from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler
from smartflow.handlers.pm_base_handler import PMHandler
from smartflow.schemas.feedback import (
    FeedbackCategoryCreate,
    FeedbackCreate,
    FeedbackListOut,
    FeedbackMergeCreate,
    FeedbackOut,
    FeedbackStatusCreate,
    FeedbackSummaryOut,
)
from smartflow.services.errors import (
    CannotMergeIntoItselfError,
    CategoryNotFoundError,
    FeedbackAlreadyMergedError,
    FeedbackNotFoundError,
)
from smartflow.services.feedback_service import (
    add_to_category,
    create_feedback,
    get_feedback,
    list_feedback,
    merge,
    update_status,
)


class FeedbackHandler(BaseHandler):
    """``/api/feedback``: post a feedback, or list the active ones."""

    async def post(self):
        """Create a feedback (rating 1-5, optional note) and answer 201 with it.

        Raises:
            HTTPError: 400/422 if the body is invalid.
        """
        data = self.parse_body(FeedbackCreate)
        async with self.session_maker.begin() as session:
            feedback = await create_feedback(session, data)

        self.set_status(201)
        self.set_header("Location", f"/api/feedback/{feedback.id}")
        self.finish(FeedbackOut.model_validate(feedback).model_dump(mode="json"))

    async def get(self):
        """Return the active (not merged) feedback, newest first, with comment counts.

        Capped at the newest 100 (no pagination yet).
        """
        async with self.session_maker() as session:
            rows = await list_feedback(session)

        items = [
            FeedbackSummaryOut(
                **FeedbackOut.model_validate(feedback).model_dump(),
                comment_count=comment_count,
            )
            for feedback, comment_count in rows
        ]
        self.finish(FeedbackListOut(items=items).model_dump(mode="json"))


class FeedbackItemHandler(BaseHandler):
    """``/api/feedback/{id}``: read one feedback."""

    async def get(self, feedback_id: str):
        """Return one feedback, merged ones included (see ``merged_into_id``).

        Args:
            feedback_id: The id from the URL.

        Raises:
            HTTPError: 404 if the feedback does not exist.
        """
        try:
            async with self.session_maker() as session:
                feedback = await get_feedback(session, int(feedback_id))
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None

        self.finish(FeedbackOut.model_validate(feedback).model_dump(mode="json"))


class FeedbackCategoryHandler(PMHandler):
    """``/api/feedback/{id}/category`` (PM): put a feedback in a category."""

    async def put(self, feedback_id: str):
        """Set the feedback's category; ``{"category_id": null}`` removes it.

        PUT because it is idempotent: sending the same body twice gives the
        same result.

        Args:
            feedback_id: The id from the URL.

        Raises:
            HTTPError: 400/422 if the body is invalid; 404 if the feedback or
                the category does not exist; 409 if the feedback was merged.
        """
        data = self.parse_body(FeedbackCategoryCreate)
        try:
            async with self.session_maker.begin() as session:
                feedback = await add_to_category(session, int(feedback_id), data)
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None
        except CategoryNotFoundError:
            raise HTTPError(404, reason="Category not found") from None
        except FeedbackAlreadyMergedError:
            raise HTTPError(
                409, reason="Feedback was merged and is read-only"
            ) from None

        self.finish(FeedbackOut.model_validate(feedback).model_dump(mode="json"))


class FeedbackStatusHandler(PMHandler):
    """``/api/feedback/{id}/status`` (PM): open or close a feedback."""

    async def put(self, feedback_id: str):
        """Set the feedback's status (open, closed_backlog, closed_solved, closed_rejected).

        Args:
            feedback_id: The id from the URL.

        Raises:
            HTTPError: 400/422 if the body is invalid; 404 if the feedback does
                not exist; 409 if it was merged.
        """
        data = self.parse_body(FeedbackStatusCreate)
        try:
            async with self.session_maker.begin() as session:
                feedback = await update_status(session, int(feedback_id), data)
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None
        except FeedbackAlreadyMergedError:
            raise HTTPError(
                409, reason="Feedback was merged and is read-only"
            ) from None

        self.finish(FeedbackOut.model_validate(feedback).model_dump(mode="json"))


class FeedbackMergeHandler(PMHandler):
    """``/api/feedback/{id}/merge`` (PM): merge a duplicate into another feedback."""

    async def post(self, feedback_id: str):
        """Merge the feedback in the URL (source) into ``target_id``.

        POST rather than PUT: merging is an action, and it can't be repeated
        (the source becomes read-only).

        Args:
            feedback_id: The source, the feedback that is merged away.

        Returns:
            Writes the target feedback, which now holds the source's comments.

        Raises:
            HTTPError: 400/422 if the body is invalid or the target is the
                source itself; 404 if either feedback does not exist; 409 if
                either one was already merged.
        """
        data = self.parse_body(FeedbackMergeCreate)
        try:
            async with self.session_maker.begin() as session:
                target = await merge(session, int(feedback_id), data)
        except CannotMergeIntoItselfError:
            raise HTTPError(422, reason="Cannot merge a feedback into itself") from None
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None
        except FeedbackAlreadyMergedError:
            raise HTTPError(409, reason="Feedback was already merged") from None

        self.finish(FeedbackOut.model_validate(target).model_dump(mode="json"))
