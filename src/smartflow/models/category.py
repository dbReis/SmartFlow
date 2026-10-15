"""The ``category`` table."""

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models.base import Base


class Category(Base):
    """A group PMs put feedback in (e.g. "Billing"). One category has many feedback.

    Attributes:
        id: Primary key.
        name: Short display name.
        description: Optional longer explanation.
    """

    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
