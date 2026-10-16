"""Request and response bodies for notations."""

from pydantic import BaseModel, ConfigDict

from smartflow.models.notation import NotationValue


class NotationCreate(BaseModel):
    """Body of `PUT /api/comments/{id}/notation`: -1, 0 or +1."""

    model_config = ConfigDict(extra="forbid")
    notation: NotationValue


class NotationOut(BaseModel):
    """A user's notation on a comment, as returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    comment_id: int
    user_id: str
    notation: int
