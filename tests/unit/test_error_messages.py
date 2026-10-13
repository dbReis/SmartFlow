import pytest
from pydantic import ValidationError

from smartflow.handlers.base import _validation_message
from smartflow.schemas.feedback import FeedbackCreate


def errors_for(payload) -> list:
    with pytest.raises(ValidationError) as exc_info:
        FeedbackCreate.model_validate(payload)
    return exc_info.value.errors(include_url=False)


def test_one_invalid_field_is_named_with_its_problem():
    message = _validation_message(errors_for({"rating": 9}))

    assert message == "rating: Input should be 1, 2, 3, 4 or 5"


def test_several_problems_are_joined_with_semicolons():
    message = _validation_message(errors_for({"rating": 9, "ratting": 5}))

    assert message == (
        "rating: Input should be 1, 2, 3, 4 or 5; "
        "ratting: Extra inputs are not permitted"
    )


def test_nested_fields_use_a_dotted_path():
    errors = [{"loc": ("items", 0, "name"), "msg": "Field required"}]

    assert _validation_message(errors) == "items.0.name: Field required"


def test_a_body_that_is_not_an_object_gets_a_plain_message():
    # Pydantic's own wording would name our internal schema class.
    message = _validation_message(errors_for([1, 2]))

    assert message == "Request body must be a JSON object"
