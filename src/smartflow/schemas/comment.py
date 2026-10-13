from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    # The feedback comes from the URL (/api/feedback/{id}/comments), not the body.
    # str_strip_whitespace: "   " becomes "" and is then rejected by min_length.
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
    """A comment in a discussion: its score is the sum of its notations."""

    score: int
    votes: int


class CommentListOut(BaseModel):
    items: list[CommentWithScoreOut]
