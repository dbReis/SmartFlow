"""Request and response bodies for comments."""

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Body of `POST /api/feedback/{id}/comments`.

    Whitespace is stripped first, so a blank comment fails `min_length`.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    comment: str = Field(
        description="Comment provided by the user to the feedback",
        max_length=2000,
        min_length=1,
    )


class CommentOut(BaseModel):
    """A comment as returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    feedback_id: int
    comment: str


class CommentWithScoreOut(CommentOut):
    """A comment in a list, with its vote totals.

    `score` is the sum of its notations (0 when it has none); `votes` is how
    many notations it received.
    """

    score: int
    votes: int


class CommentListOut(BaseModel):
    """Body of `GET /api/feedback/{id}/comments`, best score first."""

    items: list[CommentWithScoreOut]
