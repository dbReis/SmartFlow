"""``/api/feedback/{id}/comments``: read and post the discussion of a feedback."""

from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler
from smartflow.schemas.comment import (
    CommentCreate,
    CommentListOut,
    CommentOut,
    CommentWithScoreOut,
)
from smartflow.services.comment_service import create_comment, list_comments
from smartflow.services.errors import FeedbackAlreadyMergedError, FeedbackNotFoundError


class CommentsHandler(BaseHandler):
    """List and post the comments of one feedback."""

    async def get(self, feedback_id: str) -> None:
        """Return the feedback's comments with their score, best first.

        Works on merged feedback too (it then has no comments left: they moved
        to the target).

        Args:
            feedback_id: The id from the URL (always digits, thanks to the route).

        Raises:
            HTTPError: 404 if the feedback does not exist.
        """
        try:
            async with self.session_maker() as session:
                rows = await list_comments(session, int(feedback_id))
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None

        items = [
            CommentWithScoreOut(
                **CommentOut.model_validate(comment).model_dump(),
                score=score,
                votes=votes,
            )
            for comment, score, votes in rows
        ]
        self.finish(CommentListOut(items=items).model_dump(mode="json"))

    async def post(self, feedback_id: str) -> None:
        """Add a comment to the feedback and answer 201 with it.

        Args:
            feedback_id: The id from the URL.

        Raises:
            HTTPError: 400/422 if the body is invalid; 404 if the feedback does
                not exist; 409 if it was merged (merged feedback is read-only).
        """
        data = self.parse_body(CommentCreate)
        try:
            async with self.session_maker.begin() as session:
                comment = await create_comment(session, int(feedback_id), data)
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None
        except FeedbackAlreadyMergedError:
            raise HTTPError(
                409, reason="Feedback was merged and is read-only"
            ) from None

        self.set_status(201)
        self.set_header("Location", f"/api/feedback/{feedback_id}/comments")
        self.finish(CommentOut.model_validate(comment).model_dump(mode="json"))
