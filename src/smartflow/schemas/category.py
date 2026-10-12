from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=50, description="category name")
    description: str | None = Field(
        default=None,
        description="category description",
        max_length=20000,
    )


class CategoryOut(BaseModel):
    # from_attributes: build it from a SQLAlchemy Feedback object, not only a dict
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
