from smartflow.handlers.base import BaseHandler
from smartflow.schemas.feedback import FeedbackCreate, FeedbackOut
from smartflow.services.feedback_service import create_feedback


class FeedbackHandler(BaseHandler):
    async def post(self):
        data = self.parse_body(FeedbackCreate)
        async with self.session_maker.begin() as session:
            feedback = await create_feedback(session, data)

        self.set_status(201)
        self.set_header("Location", f"/api/feedback/{feedback.id}")
        self.finish(FeedbackOut.model_validate(feedback).model_dump(mode="json"))
