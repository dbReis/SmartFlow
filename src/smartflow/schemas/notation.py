from pydantic import BaseModel, ConfigDict

from smartflow.models.notation import NotationValue


class NotationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notation: NotationValue


class NotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    comment_id: int
    notation: int
