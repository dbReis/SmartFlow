"""SQLAlchemy models (the database tables).

Importing this package registers every table on ``Base.metadata``, which
``create_tables()`` needs in order to create them all.
"""

from smartflow.models.base import Base
from smartflow.models.category import Category
from smartflow.models.comment import Comment
from smartflow.models.feedback import Feedback, RatingValue
from smartflow.models.notation import Notation, NotationValue

__all__ = [
    "Base",
    "Category",
    "Comment",
    "Feedback",
    "Notation",
    "NotationValue",
    "RatingValue",
]
