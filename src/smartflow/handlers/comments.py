from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler
from smartflow.schemas.comment import CommentCreate, CommentOut
from smartflow.services.comment_service import create_comment
from smartflow.services.errors import FeedbackNotFoundError


class CommentsHandler(BaseHandler):
    """/api/feedback/{feedback_id}/comments: the comments of one feedback."""

    async def post(self, feedback_id: str) -> None:
        # Tornado passes URL groups as strings; the route guarantees digits.
        data = self.parse_body(CommentCreate)
        try:
            async with self.session_maker.begin() as session:
                comment = await create_comment(session, int(feedback_id), data)
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None

        self.set_status(201)
        self.set_header("Location", f"/api/feedback/{feedback_id}/comments")
        self.finish(CommentOut.model_validate(comment).model_dump(mode="json"))
