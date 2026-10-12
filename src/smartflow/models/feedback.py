from enum import IntEnum

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models.base import Base


class RatingValue(IntEnum):
    BAD = 1
    POOR = 2
    AVERAGE = 3
    GOOD = 4
    VERY_GOOD = 5


# Built from the enum so the allowed values are defined in one place: "1, 2, 3, 4, 5"
_ALLOWED_VALUES = ", ".join(str(value.value) for value in RatingValue)


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        # Stored as a number (not a PostgreSQL ENUM) so ratings can be averaged: AVG(rating).
        CheckConstraint(f"rating IN ({_ALLOWED_VALUES})", name="rating_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    note: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(SmallInteger)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.id", ondelete="CASCADE"), index=True
    )
