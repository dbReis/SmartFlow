"""`/api/comments/{id}/notation`: rate a comment -1, 0 or +1."""

from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler
from smartflow.schemas.notation import NotationCreate, NotationOut
from smartflow.services.errors import CommentNotFoundError
from smartflow.services.notation_service import set_notation


class NotationHandler(BaseHandler):
    """Give, or change, the user's notation on a comment."""

    async def put(self, comment_id: str) -> None:
        """Set the user's notation (-1, 0 or +1) and answer 200 with it.

        PUT because it is idempotent: one notation per user and comment, and
        sending a new value replaces the old one, like a like/dislike button.

        Args:
            comment_id: The id from the URL.

        Raises:
            HTTPError: 400/422 if the body is invalid; 401 if X-User-Id is
                missing or invalid; 404 if the comment does not exist.
        """
        user_id = self.get_user_id()
        data = self.parse_body(NotationCreate)
        try:
            async with self.session_maker.begin() as session:
                notation = await set_notation(session, int(comment_id), user_id, data)
        except CommentNotFoundError:
            raise HTTPError(404, reason="Comment not found") from None

        self.finish(NotationOut.model_validate(notation).model_dump(mode="json"))
