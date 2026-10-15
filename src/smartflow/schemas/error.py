"""The error body every failing request returns (documented in the OpenAPI spec)."""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """What went wrong: the status code and a human-readable message."""

    code: int = Field(description="HTTP status code", examples=[422])
    message: str = Field(
        description="What went wrong; for 422, one 'field: problem' per invalid field",
        examples=["rating: Input should be 1, 2, 3, 4 or 5"],
    )


class ErrorOut(BaseModel):
    """`{"error": {"code": ..., "message": ...}}`, written by BaseHandler.write_error."""

    error: ErrorDetail
