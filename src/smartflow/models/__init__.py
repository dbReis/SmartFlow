"""Database tables.

Importing this package registers every table on ``Base.metadata``, which
``create_all`` relies on: a model that is never imported is never created.
"""

from smartflow.models.base import Base
from smartflow.models.comment import Comment
from smartflow.models.feedback import Feedback, RatingValue
from smartflow.models.notation import Notation, NotationValue

__all__ = ["Base", "Comment", "Feedback", "Notation", "NotationValue", "RatingValue"]
