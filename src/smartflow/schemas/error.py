from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: int = Field(description="HTTP status code", examples=[422])
    message: str = Field(
        description="What went wrong; for 422, one 'field: problem' per invalid field",
        examples=["rating: Input should be 1, 2, 3, 4 or 5"],
    )


class ErrorOut(BaseModel):
    # The shape BaseHandler.write_error returns for every error.
    error: ErrorDetail
