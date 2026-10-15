"""Request and response bodies for feedback and the PM triage actions."""

from pydantic import BaseModel, ConfigDict, Field

from smartflow.models.feedback import FeedbackStatus, RatingValue


class FeedbackCreate(BaseModel):
    """Body of `POST /api/feedback`. Status and category are PM-only, so not accepted here."""

    model_config = ConfigDict(extra="forbid")
    rating: RatingValue
    note: str | None = Field(
        default=None,
        description="Optional note or comment about the feedback",
        max_length=20000,
    )


class FeedbackStatusCreate(BaseModel):
    """Body of `PUT /api/feedback/{id}/status`."""

    model_config = ConfigDict(extra="forbid")
    status: FeedbackStatus


class FeedbackCategoryCreate(BaseModel):
    """Body of `PUT /api/feedback/{id}/category`.

    `category_id` is required but may be null: null removes the category,
    while a missing field is a 422 (so an empty body can't clear it by mistake).
    """

    model_config = ConfigDict(extra="forbid")
    category_id: int | None


class FeedbackMergeCreate(BaseModel):
    """Body of `POST /api/feedback/{id}/merge`; the URL holds the source."""

    model_config = ConfigDict(extra="forbid")
    target_id: int = Field(description="The feedback that receives the comments")


class FeedbackOut(BaseModel):
    """A feedback as returned by the API.

    Rating and status use the enums so the OpenAPI spec lists their allowed values.
    """

    model_config = ConfigDict(from_attributes=True)
    id: int
    rating: RatingValue
    note: str | None
    status: FeedbackStatus
    category_id: int | None
    merged_into_id: int | None


class FeedbackSummaryOut(FeedbackOut):
    """A feedback in the list, with how many comments it has."""

    comment_count: int


class FeedbackListOut(BaseModel):
    """Body of `GET /api/feedback`."""

    items: list[FeedbackSummaryOut]
