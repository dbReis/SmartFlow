"""The ``comment`` table."""

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models.base import Base


class Comment(Base):
    """A comment on a feedback.

    Attributes:
        id: Primary key.
        feedback_id: The feedback it belongs to. Indexed, since comments are
            always looked up by feedback. ON DELETE CASCADE: a comment has no
            meaning without its feedback.
        comment: The text.
    """

    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    feedback_id: Mapped[int] = mapped_column(
        ForeignKey("feedback.id", ondelete="CASCADE"), index=True
    )
    comment: Mapped[str] = mapped_column(Text)
