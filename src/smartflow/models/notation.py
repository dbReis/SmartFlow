"""The ``notation`` table: -1/0/+1 votes on comments."""

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
    """The allowed votes. A comment's score is the sum of its notations."""

    DOWN = -1
    NEUTRAL = 0
    UP = 1


_ALLOWED_VALUES = ", ".join(str(value.value) for value in NotationValue)


class Notation(Base):
    """One user's vote on a comment.

    The unique key on (comment_id, user_id) lets each user hold one notation
    per comment; voting again updates it (see NotationRepository.upsert_notation).
    comment_id comes first so the key's index also serves lookups by comment.

    Attributes:
        id: Primary key.
        comment_id: The comment voted on. ON DELETE CASCADE: votes go with
            their comment.
        user_id: Who voted, from the X-User-Id header. A plain column, not a
            foreign key: there is no user table until real accounts exist.
        notation: -1, 0 or +1, enforced by a CHECK constraint built from
            NotationValue.
    """

    __tablename__ = "notation"
    __table_args__ = (
        CheckConstraint(f"notation IN ({_ALLOWED_VALUES})", name="notation_value"),
        UniqueConstraint("comment_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comment.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(String(64))
    notation: Mapped[int] = mapped_column(SmallInteger)
