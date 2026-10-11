from pydantic import BaseModel, ConfigDict, Field

from smartflow.models.feedback import RatingValue


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: RatingValue
    note: str | None = Field(
        default=None,
        description="Optional note or comment about the feedback",
        max_length=20000,
    )


class FeedbackOut(BaseModel):
    # from_attributes: build it from a SQLAlchemy Feedback object, not only a dict
    model_config = ConfigDict(from_attributes=True)
    id: int
    rating: int
    note: str | None
