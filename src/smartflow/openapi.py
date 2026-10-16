"""The API's OpenAPI spec, built from the same pydantic schemas that validate requests.

Because the component schemas are generated from the DTOs, the documentation
can't drift from what the API really accepts. Only the paths are written by
hand, with the small helpers below. Served at /openapi.json and shown by
Swagger UI at /docs.
"""

from importlib.metadata import version
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from smartflow.schemas.category import CategoryCreate, CategoryListOut, CategoryOut
from smartflow.schemas.comment import CommentCreate, CommentListOut, CommentOut
from smartflow.schemas.error import ErrorOut
from smartflow.schemas.feedback import (
    FeedbackCategoryCreate,
    FeedbackCreate,
    FeedbackListOut,
    FeedbackMergeCreate,
    FeedbackOut,
    FeedbackStatusCreate,
)
from smartflow.schemas.notation import NotationCreate, NotationOut

# Request bodies use the "validation" view of a model, responses the
# "serialization" view (they can differ, e.g. for fields with defaults).
_REQUEST_SCHEMAS = [
    FeedbackCreate,
    CommentCreate,
    NotationCreate,
    FeedbackStatusCreate,
    FeedbackCategoryCreate,
    FeedbackMergeCreate,
    CategoryCreate,
]
_RESPONSE_SCHEMAS = [
    FeedbackOut,
    FeedbackListOut,
    CommentOut,
    CommentListOut,
    NotationOut,
    CategoryOut,
    CategoryListOut,
    ErrorOut,
]

# One description per error status, reused by every operation that can return it.
_ERRORS = {
    400: "The body is not valid JSON",
    401: "Missing or invalid PM key",
    404: "A referenced resource does not exist",
    409: "The feedback was merged into another one and is read-only",
    422: "Valid JSON, but invalid or unknown fields",
    503: "PM features are not configured on the server",
}

_TAGS = [
    {"name": "feedback", "description": "Browse and post feedback"},
    {"name": "comments", "description": "Read and post the discussion of a feedback"},
    {"name": "notations", "description": "Rate comments (-1, 0, +1)"},
    {"name": "categories", "description": "Categories feedback can be put in"},
    {
        "name": "Product Manager",
        "description": "Triage feedback. Requires the PM key: click Authorize.",
    },
    {"name": "health", "description": "Service status"},
]

# Name of the security scheme; marks an operation as needing the PM key (Swagger's Authorize button).
_PM_KEY = "pmKey"


def _ref(model: type[BaseModel]) -> dict[str, str]:
    """Return a JSON reference to a model's schema under components/schemas."""
    return {"$ref": f"#/components/schemas/{model.__name__}"}


def _json(schema: dict[str, Any]) -> dict[str, Any]:
    """Wrap a schema as an ``application/json`` content entry."""
    return {"application/json": {"schema": schema}}


def _id_param(name: str, description: str) -> dict[str, Any]:
    """Describe a numeric id path parameter.

    The maximum matches the routes' ``\\d{1,9}`` pattern in app.py.

    Args:
        name: The parameter name used in the path, e.g. "feedback_id".
        description: What the id refers to.
    """
    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "integer", "minimum": 0, "maximum": 999_999_999},
    }


def _with_user_id(operation: dict[str, Any]) -> dict[str, Any]:
    """Add the X-User-Id header, and the 401 it can cause, to an operation.

    Args:
        operation: An operation built by _operation() or _get().

    Returns:
        The same operation, updated in place.
    """
    operation.setdefault("parameters", []).append(
        {
            "name": "X-User-Id",
            "in": "header",
            "required": True,
            "description": "Identifies the user (e.g. a UUID the client keeps)",
            "schema": {"type": "string", "minLength": 1, "maxLength": 64},
        }
    )
    operation["responses"]["401"] = {
        "description": "Missing or invalid X-User-Id",
        "content": _json(_ref(ErrorOut)),
    }
    return operation


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
    """Describe an operation that takes a JSON body (POST/PUT).

    Args:
        summary: One-line description shown in Swagger.
        tag: The Swagger section it appears in.
        body: Schema of the request body.
        out: Schema of the success response.
        errors: Error statuses it can return; each one gets the ErrorOut body.
        params: Path parameters, if any.
        created: True for 201 Created with a Location header, False for 200 OK.
        pm: True if it requires the PM key; adds 401 and 503 and the security
            requirement.

    Returns:
        The OpenAPI operation object.
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


def _get(
    summary: str,
    tag: str,
    out: type[BaseModel],
    errors: list[int] | None = None,
    params: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Describe a GET operation (no body, 200 OK).

    Args:
        summary: One-line description shown in Swagger.
        tag: The Swagger section it appears in.
        out: Schema of the success response.
        errors: Error statuses it can return, if any.
        params: Path parameters, if any.

    Returns:
        The OpenAPI operation object.
    """
    responses: dict[str, Any] = {
        "200": {"description": "OK", "content": _json(_ref(out))}
    }
    for code in errors or []:
        responses[str(code)] = {
            "description": _ERRORS[code],
            "content": _json(_ref(ErrorOut)),
        }
    operation: dict[str, Any] = {
        "summary": summary,
        "tags": [tag],
        "responses": responses,
    }
    if params:
        operation["parameters"] = params
    return operation


def build_spec() -> dict[str, Any]:
    """Build the full OpenAPI 3.1 document.

    The version comes from the installed package (pyproject.toml), so the
    docs always show the version that is actually running.

    Returns:
        The spec as a JSON-serialisable dict.
    """
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
                "get": _get(
                    "List active feedback, newest first, with comment counts",
                    "feedback",
                    FeedbackListOut,
                ),
                "post": _operation(
                    "Post a feedback",
                    "feedback",
                    FeedbackCreate,
                    FeedbackOut,
                    [400, 422],
                ),
            },
            "/api/feedback/{feedback_id}": {
                "get": _get(
                    "Get one feedback (merged ones too: see merged_into_id)",
                    "feedback",
                    FeedbackOut,
                    [404],
                    [_id_param("feedback_id", "The feedback to read")],
                )
            },
            "/api/feedback/{feedback_id}/comments": {
                "get": _get(
                    "List the comments of a feedback, best score first",
                    "comments",
                    CommentListOut,
                    [404],
                    [_id_param("feedback_id", "The feedback whose comments to list")],
                ),
                "post": _operation(
                    "Comment on a feedback",
                    "comments",
                    CommentCreate,
                    CommentOut,
                    [400, 404, 409, 422],
                    [_id_param("feedback_id", "The feedback to comment on")],
                ),
            },
            "/api/comments/{comment_id}/notation": {
                "put": _with_user_id(
                    _operation(
                        "Give or change your notation (-1, 0 or +1) on a comment",
                        "notations",
                        NotationCreate,
                        NotationOut,
                        [400, 404, 422],
                        [_id_param("comment_id", "The comment to rate")],
                        created=False,
                    )
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
            "/api/pm/session": {
                "get": {
                    "summary": "Check a PM key (204 if it is valid)",
                    "tags": ["Product Manager"],
                    "responses": {
                        "204": {"description": "The key is valid"},
                        **{
                            str(code): {
                                "description": _ERRORS[code],
                                "content": _json(_ref(ErrorOut)),
                            }
                            for code in (401, 503)
                        },
                    },
                    "security": [{_PM_KEY: []}],
                }
            },
            "/api/category": {
                "get": _get("List all categories", "categories", CategoryListOut),
                "post": _operation(
                    "Create a category",
                    "Product Manager",
                    CategoryCreate,
                    CategoryOut,
                    [400, 422],
                    pm=True,
                ),
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
