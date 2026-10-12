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
    # Required key; null removes the feedback from its category.
    category_id: int | None


class FeedbackMergeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_id: int = Field(description="The feedback that receives the comments")


###### OUT #####
class FeedbackOut(BaseModel):
    # from_attributes: build it from a SQLAlchemy Feedback object, not only a dict
    model_config = ConfigDict(from_attributes=True)
    id: int
    rating: int
    note: str | None
    status: str
    category_id: int | None
    merged_into_id: int | None
