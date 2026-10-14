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
    async def post(self):
        data = self.parse_body(FeedbackCreate)
        async with self.session_maker.begin() as session:
            feedback = await create_feedback(session, data)

        self.set_status(201)
        self.set_header("Location", f"/api/feedback/{feedback.id}")
        self.finish(FeedbackOut.model_validate(feedback).model_dump(mode="json"))

    async def get(self):
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
    async def get(self, feedback_id: str):
        try:
            async with self.session_maker() as session:
                feedback = await get_feedback(session, int(feedback_id))
        except FeedbackNotFoundError:
            raise HTTPError(404, reason="Feedback not found") from None

        self.finish(FeedbackOut.model_validate(feedback).model_dump(mode="json"))


class FeedbackCategoryHandler(PMHandler):
    async def put(self, feedback_id: str):
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
    async def put(self, feedback_id: str):
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
    async def post(self, feedback_id: str):
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
