"""Request and response bodies for notations."""

from pydantic import BaseModel, ConfigDict

from smartflow.models.notation import NotationValue


class NotationCreate(BaseModel):
    """Body of `POST /api/comments/{id}/notation`: -1, 0 or +1."""

    model_config = ConfigDict(extra="forbid")
    notation: NotationValue


class NotationOut(BaseModel):
    """A notation as returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    comment_id: int
    notation: int
