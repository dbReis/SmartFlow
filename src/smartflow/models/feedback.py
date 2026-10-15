"""The ``feedback`` table, with its allowed ratings and statuses."""

from enum import IntEnum, StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models.base import Base


class FeedbackStatus(StrEnum):
    """Where a feedback is in the PM's triage. New feedback is OPEN."""

    OPEN = "open"
    CLOSED_BACKLOG = "closed_backlog"
    CLOSED_SOLVED = "closed_solved"
    CLOSED_REJECTED = "closed_rejected"


class RatingValue(IntEnum):
    """The 1-5 rating a user gives."""

    BAD = 1
    POOR = 2
    AVERAGE = 3
    GOOD = 4
    VERY_GOOD = 5


# The enums are the single source of truth: the CHECK constraints below are
# built from them, so the database and the API can never disagree on what's valid.
# Plain columns + CHECK rather than PostgreSQL ENUM types, which are harder to change.
_ALLOWED_VALUES = ", ".join(str(value.value) for value in RatingValue)
_ALLOWED_STATUS_VALUES = ", ".join(f"'{value}'" for value in FeedbackStatus)


class Feedback(Base):
    """A rated piece of user feedback.

    Attributes:
        id: Primary key.
        note: Optional free text.
        rating: 1-5, enforced by a CHECK constraint.
        category_id: The category, if a PM set one. ON DELETE SET NULL:
            deleting a category un-categorises its feedback instead of deleting it.
        status: Triage status, enforced by a CHECK constraint. The default is
            set in the database (server_default), so it applies to any insert.
        merged_into_id: Set when this feedback was merged into another one; it
            is then read-only and hidden from the list. Points at the same table.
    """

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
