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
    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json; charset=utf-8")

    def prepare(self) -> None:
        log.debug(
            "request_received",
            method=self.request.method,
            path=self.request.path,
            body_bytes=len(self.request.body),
        )

    def parse_body[T: BaseModel](self, schema: type[T]) -> T:
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
        self.finish({"error": {"code": status_code, "message": self._reason}})
