"""OpenAPI 3.1 description of the API, built from the Pydantic schemas.

Request and response shapes come from the same schemas the handlers validate
with, so the documentation cannot drift from the real rules. Only the paths are
written here by hand.

The running app serves it at /openapi.json, and Swagger UI at /docs.
"""

from importlib.metadata import version
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from smartflow.schemas.category import CategoryCreate, CategoryOut
from smartflow.schemas.comment import CommentCreate, CommentOut
from smartflow.schemas.error import ErrorOut
from smartflow.schemas.feedback import (
    FeedbackCategoryCreate,
    FeedbackCreate,
    FeedbackMergeCreate,
    FeedbackOut,
    FeedbackStatusCreate,
)
from smartflow.schemas.notation import NotationCreate, NotationOut

_REQUEST_SCHEMAS = [
    FeedbackCreate,
    CommentCreate,
    NotationCreate,
    FeedbackStatusCreate,
    FeedbackCategoryCreate,
    FeedbackMergeCreate,
    CategoryCreate,
]
_RESPONSE_SCHEMAS = [FeedbackOut, CommentOut, NotationOut, CategoryOut, ErrorOut]

_ERRORS = {
    400: "The body is not valid JSON",
    401: "Missing or invalid PM key",
    404: "A referenced resource does not exist",
    409: "The feedback was merged into another one and is read-only",
    422: "Valid JSON, but invalid or unknown fields",
    503: "PM features are not configured on the server",
}

# The tags group operations in Swagger UI, in this order.
_TAGS = [
    {"name": "feedback", "description": "Post feedback"},
    {"name": "comments", "description": "Discuss a feedback"},
    {"name": "notations", "description": "Rate comments (-1, 0, +1)"},
    {
        "name": "Product Manager",
        "description": "Triage feedback. Requires the PM key: click Authorize.",
    },
    {"name": "health", "description": "Service status"},
]

# Name of the security scheme for PM endpoints (Authorization: Bearer <key>).
_PM_KEY = "pmKey"


def _ref(model: type[BaseModel]) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{model.__name__}"}


def _json(schema: dict[str, Any]) -> dict[str, Any]:
    return {"application/json": {"schema": schema}}


def _id_param(name: str, description: str) -> dict[str, Any]:
    # Routes match \d{1,9}: digits only, small enough for a PostgreSQL INTEGER.
    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "integer", "minimum": 0, "maximum": 999_999_999},
    }


def _operation(
    summary: str,
    tag: str,
    body: type[BaseModel],
    out: type[BaseModel],
    errors: list[int],
    params: list[dict[str, Any]] | None = None,
    *,
    created: bool = True,
    pm: bool = False,
) -> dict[str, Any]:
    """One operation with a JSON body and a JSON response or JSON error.

    created=True: 201 + Location header (a new resource); False: 200 (a change).
    pm=True: requires the PM key, which adds the 401 and 503 errors.
    """
    success: dict[str, Any] = {
        "description": "Created" if created else "OK",
        "content": _json(_ref(out)),
    }
    if created:
        success["headers"] = {
            "Location": {
                "description": "URL of the created resource",
                "schema": {"type": "string"},
            }
        }
    responses: dict[str, Any] = {"201" if created else "200": success}
    error_codes = sorted({*errors, 401, 503} if pm else set(errors))
    for code in error_codes:
        responses[str(code)] = {
            "description": _ERRORS[code],
            "content": _json(_ref(ErrorOut)),
        }
    operation: dict[str, Any] = {
        "summary": summary,
        "tags": [tag],
        "requestBody": {"required": True, "content": _json(_ref(body))},
        "responses": responses,
    }
    if params:
        operation["parameters"] = params
    if pm:
        operation["security"] = [{_PM_KEY: []}]
    return operation


def build_spec() -> dict[str, Any]:
    _, schemas = models_json_schema(
        [(model, "validation") for model in _REQUEST_SCHEMAS]
        + [(model, "serialization") for model in _RESPONSE_SCHEMAS],
        ref_template="#/components/schemas/{model}",
    )
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "SmartFlow API",
            "version": version("smartflow"),
            "description": "Async REST API for rated user feedback.",
        },
        # No "servers": Swagger UI then calls the server it was opened from.
        "tags": _TAGS,
        "paths": {
            "/api/health": {
                "get": {
                    "summary": "Check that the server is up",
                    "tags": ["health"],
                    "responses": {
                        "200": {
                            "description": "The server is running",
                            "content": _json(
                                {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "const": "ok"}
                                    },
                                }
                            ),
                        }
                    },
                }
            },
            "/api/feedback": {
                "post": _operation(
                    "Post a feedback",
                    "feedback",
                    FeedbackCreate,
                    FeedbackOut,
                    [400, 422],
                )
            },
            "/api/feedback/{feedback_id}/comments": {
                "post": _operation(
                    "Comment on a feedback",
                    "comments",
                    CommentCreate,
                    CommentOut,
                    [400, 404, 409, 422],
                    [_id_param("feedback_id", "The feedback to comment on")],
                )
            },
            "/api/comments/{comment_id}/notation": {
                "post": _operation(
                    "Give a notation (-1, 0 or +1) to a comment",
                    "notations",
                    NotationCreate,
                    NotationOut,
                    [400, 404, 422],
                    [_id_param("comment_id", "The comment to rate")],
                )
            },
            "/api/feedback/{feedback_id}/status": {
                "put": _operation(
                    "Set the status of a feedback",
                    "Product Manager",
                    FeedbackStatusCreate,
                    FeedbackOut,
                    [400, 404, 409, 422],
                    [_id_param("feedback_id", "The feedback to update")],
                    created=False,
                    pm=True,
                )
            },
            "/api/feedback/{feedback_id}/category": {
                "put": _operation(
                    "Put a feedback in a category (null removes it)",
                    "Product Manager",
                    FeedbackCategoryCreate,
                    FeedbackOut,
                    [400, 404, 409, 422],
                    [_id_param("feedback_id", "The feedback to categorise")],
                    created=False,
                    pm=True,
                )
            },
            "/api/feedback/{feedback_id}/merge": {
                "post": _operation(
                    "Merge a feedback into another one",
                    "Product Manager",
                    FeedbackMergeCreate,
                    FeedbackOut,
                    [400, 404, 409, 422],
                    [_id_param("feedback_id", "The feedback merged away (the source)")],
                    created=False,
                    pm=True,
                )
            },
            "/api/category": {
                "post": _operation(
                    "Create a category",
                    "Product Manager",
                    CategoryCreate,
                    CategoryOut,
                    [400, 422],
                    pm=True,
                )
            },
        },
        "components": {
            "schemas": schemas["$defs"],
            "securitySchemes": {
                _PM_KEY: {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "The PM key (SMARTFLOW_PM_API_KEY on the server)",
                }
            },
        },
    }
