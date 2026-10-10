from enum import IntEnum

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models.base import Base


class NotationValue(IntEnum):
    DOWN = -1
    NEUTRAL = 0
    UP = 1


# Built from the enum so the allowed values are defined in one place: "-1, 0, 1"
_ALLOWED_VALUES = ", ".join(str(value.value) for value in NotationValue)


class Notation(Base):
    __tablename__ = "notation"
    __table_args__ = (
        # Stored as a number (not a PostgreSQL ENUM) so a score is just SUM(notation).
        CheckConstraint(f"notation IN ({_ALLOWED_VALUES})", name="notation_value"),
        # One notation per user per comment, enforced by the database so two
        # concurrent requests cannot both insert one.
        UniqueConstraint("comment_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comment.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(String(64))  # from the X-User-Id header
    notation: Mapped[int] = mapped_column(SmallInteger)
