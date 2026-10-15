"""Domain errors raised by the services.

Services don't know about HTTP; handlers translate these into status codes
(404, 409, 422). Each error keeps the id involved, for logs and tests.
"""


class FeedbackNotFoundError(Exception):
    """The feedback does not exist (HTTP 404)."""

    def __init__(self, feedback_id: int) -> None:
        super().__init__(f"Feedback {feedback_id} not found")
        self.feedback_id = feedback_id


class CommentNotFoundError(Exception):
    """The comment does not exist (HTTP 404)."""

    def __init__(self, comment_id: int) -> None:
        super().__init__(f"Comment {comment_id} not found")
        self.comment_id = comment_id


class CategoryNotFoundError(Exception):
    """The category does not exist (HTTP 404)."""

    def __init__(self, category_id: int) -> None:
        super().__init__(f"Category {category_id} not found")
        self.category_id = category_id


class CannotMergeIntoItselfError(Exception):
    """A merge whose source and target are the same feedback (HTTP 422)."""

    def __init__(self, feedback_id: int) -> None:
        super().__init__(f"Cannot merge feedback {feedback_id} into itself")
        self.feedback_id = feedback_id


class FeedbackAlreadyMergedError(Exception):
    """The feedback was merged into another one and is read-only (HTTP 409)."""

    def __init__(self, feedback_id: int) -> None:
        super().__init__(f"Feedback {feedback_id} already merged")
        self.feedback_id = feedback_id
