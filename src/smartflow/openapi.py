"""OpenAPI 3.1 description of the API, built from the Pydantic schemas.

Request and response shapes come from the same schemas the handlers validate
with, so the documentation cannot drift from the real rules. Only the paths are
written here by hand.

The running app serves it at /docs (Swagger UI) and /openapi.json. For GitHub
Pages, write both files into a folder:  python -m smartflow.openapi site
"""

import argparse
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from smartflow.schemas.comment import CommentCreate, CommentOut
from smartflow.schemas.error import ErrorOut
from smartflow.schemas.feedback import FeedbackCreate, FeedbackOut
from smartflow.schemas.notation import NotationCreate, NotationOut

DEFAULT_SERVER_URL = "http://localhost:8888"
SWAGGER_UI_VERSION = "5.33.1"

_REQUEST_SCHEMAS = [FeedbackCreate, CommentCreate, NotationCreate]
_RESPONSE_SCHEMAS = [FeedbackOut, CommentOut, NotationOut, ErrorOut]

_ERRORS = {
    400: "The body is not valid JSON",
    404: "A referenced resource does not exist",
    422: "Valid JSON, but invalid or unknown fields",
}


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


def _create(
    summary: str,
    tag: str,
    body: type[BaseModel],
    out: type[BaseModel],
    errors: list[int],
    params: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A POST that creates a resource: 201 + Location header, or a JSON error."""
    responses: dict[str, Any] = {
        "201": {
            "description": "Created",
            "headers": {
                "Location": {
                    "description": "URL of the created resource",
                    "schema": {"type": "string"},
                }
            },
            "content": _json(_ref(out)),
        }
    }
    for code in errors:
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
    return operation


def build_spec(server_url: str = DEFAULT_SERVER_URL) -> dict[str, Any]:
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
        "servers": [{"url": server_url}],
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
                "post": _create(
                    "Post a feedback",
                    "feedback",
                    FeedbackCreate,
                    FeedbackOut,
                    [400, 422],
                )
            },
            "/api/feedback/{feedback_id}/comments": {
                "post": _create(
                    "Comment on a feedback",
                    "comments",
                    CommentCreate,
                    CommentOut,
                    [400, 404, 422],
                    [_id_param("feedback_id", "The feedback to comment on")],
                )
            },
            "/api/comments/{comment_id}/notation": {
                "post": _create(
                    "Give a notation (-1, 0 or +1) to a comment",
                    "notations",
                    NotationCreate,
                    NotationOut,
                    [400, 404, 422],
                    [_id_param("comment_id", "The comment to rate")],
                )
            },
        },
        "components": {"schemas": schemas["$defs"]},
    }


def swagger_html(spec_url: str) -> str:
    """The Swagger UI page: loads Swagger from a CDN and points it at spec_url."""
    cdn = f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>SmartFlow API</title>
    <link rel="stylesheet" href="{cdn}/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="{cdn}/swagger-ui-bundle.js"></script>
    <script>
      SwaggerUIBundle({{ url: "{spec_url}", dom_id: "#swagger-ui" }});
    </script>
  </body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write the docs site (index.html + openapi.json) into a folder."
    )
    parser.add_argument("output_dir", type=Path, help="folder to write, e.g. site")
    parser.add_argument(
        "--server-url",
        default=DEFAULT_SERVER_URL,
        help=f"API base URL used by 'Try it out' (default: {DEFAULT_SERVER_URL})",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    spec = json.dumps(build_spec(args.server_url), indent=2) + "\n"
    (args.output_dir / "openapi.json").write_text(spec)
    (args.output_dir / "index.html").write_text(swagger_html("openapi.json"))


if __name__ == "__main__":
    main()
