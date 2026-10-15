"""Request and response bodies for categories."""

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    """Body of `POST /api/category`."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=50, description="category name")
    description: str | None = Field(
        default=None,
        description="category description",
        max_length=20000,
    )


class CategoryOut(BaseModel):
    """A category as returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None


class CategoryListOut(BaseModel):
    """Body of `GET /api/category`. A wrapping object, so fields can be added later."""

    items: list[CategoryOut]
