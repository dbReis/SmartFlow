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
        super().__init__(f"Category {category_id} not found")
        self.category_id = category_id


class CannotMergeIntoItselfError(Exception):
    def __init__(self, feedback_id: int) -> None:
        super().__init__(f"Cannot merge feedback {feedback_id} into itself")
        self.feedback_id = feedback_id


class FeedbackAlreadyMergedError(Exception):
    def __init__(self, feedback_id: int) -> None:
        super().__init__(f"Feedback {feedback_id} already merged")
        self.feedback_id = feedback_id
