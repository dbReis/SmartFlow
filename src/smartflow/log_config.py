import logging
import os
import sys
from typing import Literal

import structlog
from tornado.web import RequestHandler

LogFormat = Literal["console", "json"]

ACCESS_LOGGER = "tornado.access"

_RESET = "\033[0m"
_LEVEL_COLORS = {
    "debug": "\033[2m",
    "info": "\033[32m",
    "warning": "\033[33m",
    "error": "\033[31m",
    "critical": "\033[1;31m",
}

_SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]


def _use_colors() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _make_plain_renderer(colors: bool) -> structlog.typing.Processor:
    def render(_logger: object, _method: str, event_dict: dict) -> str:
        timestamp = event_dict.pop("timestamp", "")
        level = event_dict.pop("level", "")
        logger = event_dict.pop("logger", "")
        event = event_dict.pop("event", "")
        exception = event_dict.pop("exception", None)

        if colors and level in _LEVEL_COLORS:
            level = f"{_LEVEL_COLORS[level]}{level}{_RESET}"

        parts = [timestamp, level]
        if logger != ACCESS_LOGGER:
            parts.append(str(event))
        parts += [f"{key}={value}" for key, value in event_dict.items()]

        line = " ".join(parts)
        return f"{line}\n{exception}" if exception else line

    return render


def configure_logging(level: str = "INFO", log_format: LogFormat = "console") -> None:
    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    if log_format == "json":
        final_processors = [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        final_processors = [
            structlog.processors.format_exc_info,
            _make_plain_renderer(colors=_use_colors()),
        ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *final_processors,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


_access_log = structlog.get_logger(ACCESS_LOGGER)


def log_request(handler: RequestHandler) -> None:
    status = handler.get_status()
    if status < 400:
        log = _access_log.info
    elif status < 500:
        log = _access_log.warning
    else:
        log = _access_log.error
    log(
        "request",
        method=handler.request.method,
        path=handler.request.path,
        status=status,
    )
