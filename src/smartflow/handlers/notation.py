"""``/api/comments/{id}/notation``: rate a comment -1, 0 or +1."""

from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler
from smartflow.schemas.notation import NotationCreate, NotationOut
from smartflow.services.errors import CommentNotFoundError
from smartflow.services.notation_service import create_notation


class NotationHandler(BaseHandler):
    """Give a notation to a comment."""

    async def post(self, comment_id: str) -> None:
        """Record a notation (-1, 0 or +1) and answer 201 with it.

        Each call adds one notation; users aren't identified yet, so a
        notation can't be changed or limited to one per user.

        Args:
            comment_id: The id from the URL.

        Raises:
            HTTPError: 400/422 if the body is invalid; 404 if the comment does
                not exist.
        """
        data = self.parse_body(NotationCreate)
        try:
            async with self.session_maker.begin() as session:
                notation = await create_notation(session, int(comment_id), data)
        except CommentNotFoundError:
            raise HTTPError(404, reason="Comment not found") from None

        self.set_status(201)
        self.set_header("Location", f"/api/comments/{comment_id}/notation")
        self.finish(NotationOut.model_validate(notation).model_dump(mode="json"))
