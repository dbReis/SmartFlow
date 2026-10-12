from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler
from smartflow.handlers.pm_base_handler import PMHandler
from smartflow.schemas.feedback import (
    FeedbackCategory,
    FeedbackCategoryOut,
    FeedbackCreate,
    FeedbackOut,
)
from smartflow.services.errors import CategoryNotFoundError, FeedbackNotFoundError
from smartflow.services.feedback_service import add_to_category, create_feedback


class FeedbackHandler(BaseHandler):
    async def post(self):
        data = self.parse_body(FeedbackCreate)
        async with self.session_maker.begin() as session:
            feedback = await create_feedback(session, data)

        self.set_status(201)
        self.set_header("Location", f"/api/feedback/{feedback.id}")
        self.finish(FeedbackOut.model_validate(feedback).model_dump(mode="json"))


class FeedbackCategoryHandler(PMHandler):
    async def put(self, feedback_id: str):
        data = self.parse_body(FeedbackCategory)
        try:
            async with self.session_maker.begin() as session:
                feedback = await add_to_category(session, int(feedback_id), data)
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None
        except CategoryNotFoundError:
            raise HTTPError(404, reason="Category not found") from None

        self.set_status(200)
        self.set_header("Location", f"/api/feedback/{feedback.id}/category")
        self.finish(
            FeedbackCategoryOut.model_validate(feedback).model_dump(mode="json")
        )
