import json
from typing import Any

import structlog
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tornado.web import HTTPError, RequestHandler

log = structlog.get_logger(__name__)


class BaseHandler(RequestHandler):
    """Parent of every API handler: JSON in, JSON out, JSON errors."""

    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker
        self._validation_errors: list[dict[str, Any]] | None = None

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json; charset=utf-8")

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

        Broken JSON → 400. Valid JSON with invalid values → 422 with details.
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
            # exc.json() makes every detail JSON-safe before it reaches the response.
            self._validation_errors = json.loads(exc.json(include_url=False))
            # Field and error type only: the submitted values may be personal data.
            log.info(
                "request_validation_failed",
                schema=schema.__name__,
                errors=[
                    {"field": ".".join(map(str, e["loc"])), "type": e["type"]}
                    for e in self._validation_errors
                ],
            )
            raise HTTPError(422, reason="Validation failed") from None

        log.debug("request_body_parsed", schema=schema.__name__)
        return parsed

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        """Called by Tornado for every error: turn it into a JSON body.

        Unexpected exceptions only expose the generic reason ("Internal Server
        Error"); the traceback goes to the logs, never to the client.
        """
        error: dict[str, Any] = {"code": status_code, "message": self._reason}
        if status_code == 422 and self._validation_errors:
            error["details"] = self._validation_errors
        self.finish({"error": error})
