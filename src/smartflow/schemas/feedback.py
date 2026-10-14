from pydantic import BaseModel, ConfigDict, Field

from smartflow.models.feedback import FeedbackStatus, RatingValue


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: RatingValue
    note: str | None = Field(
        default=None,
        description="Optional note or comment about the feedback",
        max_length=20000,
    )


class FeedbackStatusCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: FeedbackStatus


class FeedbackCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_id: int | None


class FeedbackMergeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_id: int = Field(description="The feedback that receives the comments")


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rating: RatingValue
    note: str | None
    status: FeedbackStatus
    category_id: int | None
    merged_into_id: int | None


class FeedbackSummaryOut(FeedbackOut):
    comment_count: int


class FeedbackListOut(BaseModel):
    items: list[FeedbackSummaryOut]
