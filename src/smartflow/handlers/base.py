"""Shared base for every API handler.

BaseHandler gives all endpoints the same behaviour: the injected session
factory, JSON responses, request validation (400/422) and one JSON error
format for every failure. Endpoint handlers extend it instead of Tornado's
RequestHandler.
"""

import json
from typing import Any

import structlog
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tornado.web import HTTPError, RequestHandler

log = structlog.get_logger(__name__)


def _field(error: Any) -> str:
    """Turn a pydantic error location into a dotted path, e.g. "items.0.name"."""
    return ".".join(str(part) for part in error["loc"])


def _validation_message(errors: list[Any]) -> str:
    """Join pydantic errors into one client-facing line.

    Each error becomes "field: problem", e.g.
    "rating: Input should be 1, 2, 3, 4 or 5; ratting: Extra inputs are not permitted".
    An error about the whole body (no field) gets a plain message instead of
    pydantic's, which would name our internal schema class.
    """
    return "; ".join(
        f"{_field(e)}: {e['msg']}" if e["loc"] else "Request body must be a JSON object"
        for e in errors
    )


class BaseHandler(RequestHandler):
    """Base class for every SmartFlow endpoint.

    Handlers open their own session per request: ``self.session_maker.begin()``
    for writes (commit on success, rollback on error) and
    ``self.session_maker()`` for reads.
    """

    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        """Store the session factory passed in by make_app() (the route's deps dict).

        Injected rather than imported so every handler shares the app's single
        engine.

        Args:
            session_maker: Factory that opens one database session per request.
        """
        self.session_maker = session_maker

    def set_default_headers(self) -> None:
        """Mark every response, errors included, as JSON.

        Tornado calls this before each request and again before writing an error,
        so headers set here are never lost.
        """
        self.set_header("Content-Type", "application/json; charset=utf-8")

    def prepare(self) -> None:
        """Log every incoming request before it reaches get()/post()/put().

        Tornado calls this hook first on each request. Subclasses extend it:
        PMHandler calls super().prepare(), then checks the PM key.
        Logs the body's size only, never its content (it may hold user text).
        """
        log.debug(
            "request_received",
            method=self.request.method,
            path=self.request.path,
            body_bytes=len(self.request.body),
        )

    def parse_body[T: BaseModel](self, schema: type[T]) -> T:
        """Parse the JSON body and validate it against a schema.

        Args:
            schema: The pydantic model the body must match, e.g. FeedbackCreate.

        Returns:
            A validated instance of that schema.

        Raises:
            HTTPError: 400 if the body is not valid JSON; 422 if it is JSON but
                breaks the schema's rules (the message names each invalid field).
        """
        try:
            data = json.loads(self.request.body)
        except ValueError as exc:
            log.info(
                "request_body_invalid_json", schema=schema.__name__, reason=str(exc)
            )
            raise HTTPError(400, reason="Request body must be valid JSON") from None

        try:
            parsed = schema.model_validate(data)
        except ValidationError as exc:
            errors = exc.errors(include_url=False)
            log.info(
                "request_validation_failed",
                schema=schema.__name__,
                errors=[{"field": _field(e), "type": e["type"]} for e in errors],
            )
            raise HTTPError(422, reason=_validation_message(errors)) from None

        log.debug("request_body_parsed", schema=schema.__name__)
        return parsed

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        """Write every error, expected or not, as {"error": {"code", "message"}}.

        Tornado calls this for any HTTPError and for unexpected exceptions (500).
        The message is the HTTP reason only: tracebacks go to the logs, never to
        the client.
        """
        self.finish({"error": {"code": status_code, "message": self._reason}})

    def get_user_id(self) -> str:
        """Identify the user from the X-User-Id header.

        Users have no accounts yet: the client sends its own id (the UI uses a
        UUID kept in localStorage). It is what makes a notation unique per
        user. With JWT later, only this method changes.

        Returns:
            The user id, without surrounding whitespace.

        Raises:
            HTTPError: 401 if the header is missing, blank or longer than 64
                characters (the size of the notation.user_id column).
        """
        user_id = self.request.headers.get("X-User-Id", "").strip()
        if not user_id or len(user_id) > 64:
            raise HTTPError(401, reason="Missing or invalid X-User-Id")
        return user_id
