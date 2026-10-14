from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    comment: str = Field(
        description="Comment provided by the user to the feedback",
        max_length=2000,
        min_length=1,
    )


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    feedback_id: int
    comment: str


class CommentWithScoreOut(CommentOut):
    score: int
    votes: int


class CommentListOut(BaseModel):
    items: list[CommentWithScoreOut]
