"""Logging setup: structlog for the app, one format for Tornado's and SQLAlchemy's logs too.

Every log line, ours or a library's, goes through the same processors and is
printed to stdout, either as readable text or as JSON.
"""

import logging
import os
import sys
from typing import Literal

import structlog
from tornado.web import RequestHandler

LogFormat = Literal["console", "json"]
"""The output formats ``configure_logging`` accepts."""

ACCESS_LOGGER = "tornado.access"
"""Logger used for the one-line-per-request access log."""

_RESET = "\033[0m"
_LEVEL_COLORS = {
    "debug": "\033[2m",
    "info": "\033[32m",
    "warning": "\033[33m",
    "error": "\033[31m",
    "critical": "\033[1;31m",
}

# Run on every event, from structlog and from the standard logging module alike.
_SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]


def _use_colors() -> bool:
    """Colour the level only in a terminal, never in files or log collectors.

    Honours the NO_COLOR convention (https://no-color.org).
    """
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _make_plain_renderer(colors: bool) -> structlog.typing.Processor:
    """Build the renderer for the ``console`` format.

    Lines look like ``<timestamp> <level> <event> key=value ...``. Access log
    lines omit the event name, since it is always "request".

    Args:
        colors: Whether to wrap the level in ANSI colour codes.

    Returns:
        A structlog processor that turns an event dict into one line of text
        (plus the traceback, if any).
    """

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
    """Route all logging (structlog and the standard library) to stdout.

    The standard library's root logger gets a single handler using structlog's
    ProcessorFormatter, so Tornado and SQLAlchemy messages share our format.
    Call it once, at startup, before anything is logged.

    Args:
        level: Minimum level to output, e.g. "DEBUG" or "info".
        log_format: "console" for readable lines, "json" for one JSON object per line.
    """
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
    # Drop any handler added before us so each line is printed once.
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


_access_log = structlog.get_logger(ACCESS_LOGGER)


def log_request(handler: RequestHandler) -> None:
    """Write one access log line per finished request.

    Passed to Tornado as ``log_function``. The level follows the status: info
    for success, warning for client errors (4xx), error for server errors
    (5xx). Only the method, path and status are logged, never bodies or headers.

    Args:
        handler: The handler that served the request.
    """
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
