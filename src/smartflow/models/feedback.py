from enum import IntEnum, StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models.base import Base


class FeedbackStatus(StrEnum):
    OPEN = "open"
    CLOSED_BACKLOG = "closed_backlog"
    CLOSED_SOLVED = "closed_solved"
    CLOSED_REJECTED = "closed_rejected"


class RatingValue(IntEnum):
    BAD = 1
    POOR = 2
    AVERAGE = 3
    GOOD = 4
    VERY_GOOD = 5


_ALLOWED_VALUES = ", ".join(str(value.value) for value in RatingValue)
_ALLOWED_STATUS_VALUES = ", ".join(f"'{value}'" for value in FeedbackStatus)


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(f"rating IN ({_ALLOWED_VALUES})", name="rating_value"),
        CheckConstraint(f"status in ({_ALLOWED_STATUS_VALUES})", name="status_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    note: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(SmallInteger)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("category.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), server_default=FeedbackStatus.OPEN.value
    )
    merged_into_id: Mapped[int | None] = mapped_column(
        ForeignKey("feedback.id", ondelete="SET NULL"), index=True
    )
