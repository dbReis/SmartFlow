"""Domain errors raised by services.

Services know nothing about HTTP: they raise these, and handlers translate
them into status codes (e.g. FeedbackNotFoundError → 404).
"""


class FeedbackNotFoundError(Exception):
    def __init__(self, feedback_id: int) -> None:
        super().__init__(f"Feedback {feedback_id} not found")
        self.feedback_id = feedback_id


class CommentNotFoundError(Exception):
    def __init__(self, comment_id: int) -> None:
        super().__init__(f"Comment {comment_id} not found")
        self.comment_id = comment_id


class CategoryNotFoundError(Exception):
    def __init__(self, category_id: int) -> None:
        super().__init__(f"Feedback {category_id} not found")
        self.feedback_id = category_id
