import json
from typing import Any

import structlog
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tornado.web import HTTPError, RequestHandler

log = structlog.get_logger(__name__)


def _field(error: Any) -> str:
    return ".".join(str(part) for part in error["loc"])


def _validation_message(errors: list[Any]) -> str:
    return "; ".join(
        f"{_field(e)}: {e['msg']}" if e["loc"] else "Request body must be a JSON object"
        for e in errors
    )


class BaseHandler(RequestHandler):
    """Parent of every API handler: JSON in, JSON out, JSON errors."""

    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self._set_cors_headers()

    def _set_cors_headers(self) -> None:
        """Allow browser pages from the configured origins to call the API.

        Browsers block JavaScript from reading responses from another origin
        (scheme + host + port) unless the response allows it. Only origins in
        the allow-list get the headers, never "*": other websites stay blocked.
        Runs for every response, errors included (Tornado re-applies the
        default headers before writing an error).
        """
        origin = self.request.headers.get("Origin")
        if origin is None or origin not in self.settings.get("cors_origins", []):
            return
        self.set_header("Access-Control-Allow-Origin", origin)
        # The answer depends on the Origin header: caches must not share it.
        self.set_header("Vary", "Origin")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.set_header(
            "Access-Control-Allow-Headers", "Content-Type, Authorization, X-User-Id"
        )
        # Let the UI read the Location header of 201 responses.
        self.set_header("Access-Control-Expose-Headers", "Location")
        # Browsers may reuse a preflight answer for 10 minutes.
        self.set_header("Access-Control-Max-Age", "600")

    def options(self, *args: str) -> None:
        """Answer the browser's CORS preflight; the headers are already set."""
        self.set_status(204)
        self.finish()

    def prepare(self) -> None:
        """Runs before every get/post/..."""
        log.debug(
            "request_received",
            method=self.request.method,
            path=self.request.path,
            body_bytes=len(self.request.body),
        )

    def parse_body[T: BaseModel](self, schema: type[T]) -> T:
        """Request bytes → JSON → validated schema object.

        Broken JSON → 400. Valid JSON with invalid values → 422, with a message
        naming each invalid field (e.g. "rating: Input should be 1, 2, 3, 4 or 5").
        """
        try:
            data = json.loads(self.request.body)
        except ValueError as exc:  # json.JSONDecodeError is a ValueError
            log.info(
                "request_body_invalid_json", schema=schema.__name__, reason=str(exc)
            )
            raise HTTPError(400, reason="Request body must be valid JSON") from None

        try:
            parsed = schema.model_validate(data)
        except ValidationError as exc:
            errors = exc.errors(include_url=False)
            # Field and error type only: the submitted values may be personal data.
            log.info(
                "request_validation_failed",
                schema=schema.__name__,
                errors=[{"field": _field(e), "type": e["type"]} for e in errors],
            )
            raise HTTPError(422, reason=_validation_message(errors)) from None

        log.debug("request_body_parsed", schema=schema.__name__)
        return parsed

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        """Called by Tornado for every error: turn it into a JSON body.

        Unexpected exceptions only expose the generic reason ("Internal Server
        Error"); the traceback goes to the logs, never to the client.
        """
        self.finish({"error": {"code": status_code, "message": self._reason}})
