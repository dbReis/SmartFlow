"""Unit tests for the request schemas: the API's input rules.

Every 422 the API returns comes from these schemas, so each rule is tested
here, without a database or a server.

Pattern: a fixture returns a *valid* payload; each test changes one thing.
"""

import pytest
from pydantic import BaseModel, ValidationError

from smartflow.models.feedback import FeedbackStatus, RatingValue
from smartflow.models.notation import NotationValue
from smartflow.schemas.category import CategoryCreate
from smartflow.schemas.comment import CommentCreate
from smartflow.schemas.feedback import (
    FeedbackCategoryCreate,
    FeedbackCreate,
    FeedbackMergeCreate,
    FeedbackStatusCreate,
)
from smartflow.schemas.notation import NotationCreate


def rejected_fields(schema: type[BaseModel], payload: dict) -> dict[str, str]:
    """Validate a payload that must fail; return {field: pydantic error type}."""
    with pytest.raises(ValidationError) as exc_info:
        schema.model_validate(payload)
    return {
        ".".join(str(part) for part in error["loc"]): error["type"]
        for error in exc_info.value.errors()
    }


# --- Fixtures: one valid payload per schema ---------------------------------


@pytest.fixture
def feedback_payload() -> dict:
    return {"rating": 4, "note": "Loading is slow"}


@pytest.fixture
def comment_payload() -> dict:
    return {"comment": "Same for me on mobile"}


# --- FeedbackCreate ----------------------------------------------------------


def test_feedback_accepts_valid_payload(feedback_payload):
    feedback = FeedbackCreate.model_validate(feedback_payload)

    assert feedback.rating is RatingValue.GOOD
    assert feedback.note == "Loading is slow"


def test_feedback_note_is_optional(feedback_payload):
    del feedback_payload["note"]

    assert FeedbackCreate.model_validate(feedback_payload).note is None


@pytest.mark.parametrize("rating", [1, 2, 3, 4, 5])
def test_feedback_accepts_every_rating_from_1_to_5(feedback_payload, rating):
    feedback_payload["rating"] = rating

    assert FeedbackCreate.model_validate(feedback_payload).rating == rating


@pytest.mark.parametrize("rating", [0, 6, -1, 4.5, "abc", None])
def test_feedback_rejects_rating_outside_1_to_5(feedback_payload, rating):
    feedback_payload["rating"] = rating

    assert rejected_fields(FeedbackCreate, feedback_payload) == {"rating": "enum"}


def test_feedback_requires_rating(feedback_payload):
    del feedback_payload["rating"]

    assert rejected_fields(FeedbackCreate, feedback_payload) == {"rating": "missing"}


def test_feedback_rejects_too_long_note(feedback_payload):
    feedback_payload["note"] = "x" * 20_001

    assert rejected_fields(FeedbackCreate, feedback_payload) == {
        "note": "string_too_long"
    }


@pytest.mark.parametrize("field", ["status", "category_id", "id", "ratting"])
def test_feedback_rejects_fields_the_client_may_not_set(feedback_payload, field):
    # status and category are PM decisions; id comes from the database;
    # "ratting" is a typo that must be reported, not silently ignored.
    feedback_payload[field] = "anything"

    assert rejected_fields(FeedbackCreate, feedback_payload) == {
        field: "extra_forbidden"
    }


# --- CommentCreate -----------------------------------------------------------


def test_comment_strips_surrounding_whitespace(comment_payload):
    comment_payload["comment"] = "  Same here  "

    assert CommentCreate.model_validate(comment_payload).comment == "Same here"


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_comment_rejects_blank_text(comment_payload, text):
    comment_payload["comment"] = text

    assert rejected_fields(CommentCreate, comment_payload) == {
        "comment": "string_too_short"
    }


def test_comment_rejects_too_long_text(comment_payload):
    comment_payload["comment"] = "x" * 2_001

    assert rejected_fields(CommentCreate, comment_payload) == {
        "comment": "string_too_long"
    }


def test_comment_rejects_feedback_id_in_body(comment_payload):
    # The feedback comes from the URL (/api/feedback/{id}/comments).
    comment_payload["feedback_id"] = 2

    assert rejected_fields(CommentCreate, comment_payload) == {
        "feedback_id": "extra_forbidden"
    }


# --- NotationCreate ----------------------------------------------------------


@pytest.mark.parametrize("value", [-1, 0, 1])
def test_notation_accepts_minus_one_zero_and_plus_one(value):
    notation = NotationCreate.model_validate({"notation": value})

    assert notation.notation is NotationValue(value)


@pytest.mark.parametrize("value", [2, -2, 0.5, "up", None])
def test_notation_rejects_other_values(value):
    assert rejected_fields(NotationCreate, {"notation": value}) == {"notation": "enum"}


# --- PM inputs ---------------------------------------------------------------


@pytest.mark.parametrize("status", list(FeedbackStatus))
def test_status_accepts_every_known_status(status):
    assert (
        FeedbackStatusCreate.model_validate({"status": status.value}).status is status
    )


@pytest.mark.parametrize("status", ["done", "closed (solved)", "OPEN", ""])
def test_status_rejects_unknown_values(status):
    assert rejected_fields(FeedbackStatusCreate, {"status": status}) == {
        "status": "enum"
    }


def test_category_id_null_means_uncategorise():
    assert (
        FeedbackCategoryCreate.model_validate({"category_id": None}).category_id is None
    )


def test_category_id_key_is_required():
    # {} must not silently uncategorise: the PM has to send null explicitly.
    assert rejected_fields(FeedbackCategoryCreate, {}) == {"category_id": "missing"}


def test_merge_requires_target_id():
    assert rejected_fields(FeedbackMergeCreate, {}) == {"target_id": "missing"}


@pytest.mark.parametrize(
    ("name", "error"),
    [("", "string_too_short"), ("x" * 51, "string_too_long")],
)
def test_category_name_length_is_limited(name, error):
    assert rejected_fields(CategoryCreate, {"name": name}) == {"name": error}
