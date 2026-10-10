from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models.base import Base


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Deleting a feedback deletes its comments (and, through them, their notations).
    feedback_id: Mapped[int] = mapped_column(
        ForeignKey("feedback.id", ondelete="CASCADE"), index=True
    )
    comment: Mapped[str] = mapped_column(Text)
