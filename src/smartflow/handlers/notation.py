from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler
from smartflow.schemas.notation import NotationCreate, NotationOut
from smartflow.services.errors import CommentNotFoundError
from smartflow.services.notation_service import create_notation


class NotationHandler(BaseHandler):
    async def post(self, comment_id: str) -> None:
        data = self.parse_body(NotationCreate)
        try:
            async with self.session_maker.begin() as session:
                notation = await create_notation(session, int(comment_id), data)
        except CommentNotFoundError:
            raise HTTPError(404, reason="Comment not found") from None

        self.set_status(201)
        self.set_header("Location", f"/api/comments/{comment_id}/notation")
        self.finish(NotationOut.model_validate(notation).model_dump(mode="json"))
