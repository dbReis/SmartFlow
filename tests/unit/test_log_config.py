import json
import logging

import pytest
import structlog

from smartflow.log_config import _make_plain_renderer, configure_logging


@pytest.fixture(autouse=True)
def restore_logging():
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


def json_lines(capsys) -> list[dict]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def test_json_format_renders_structlog_event(capsys):
    configure_logging("INFO", "json")

    structlog.get_logger("smartflow").info("vote_cast", comment_id=12, value=1)

    [entry] = json_lines(capsys)
    assert entry["event"] == "vote_cast"
    assert entry["comment_id"] == 12
    assert entry["level"] == "info"
    assert entry["logger"] == "smartflow"
    assert "timestamp" in entry


def test_stdlib_loggers_use_same_format(capsys):
    configure_logging("INFO", "json")

    logging.getLogger("tornado.application").warning("something odd")

    [entry] = json_lines(capsys)
    assert entry["event"] == "something odd"
    assert entry["logger"] == "tornado.application"


def test_context_vars_are_added_to_every_line(capsys):
    configure_logging("INFO", "json")
    structlog.contextvars.bind_contextvars(request_id="abc")

    structlog.get_logger().info("first")
    logging.getLogger("tornado.general").info("second")

    assert [e["request_id"] for e in json_lines(capsys)] == ["abc", "abc"]


def test_level_filters_lower_records(capsys):
    configure_logging("WARNING", "json")

    structlog.get_logger().info("hidden")

    assert json_lines(capsys) == []


def test_console_format_is_one_plain_line(capsys):
    configure_logging("INFO", "console")

    structlog.get_logger("smartflow").info("server_started", port=8888)

    timestamp, rest = capsys.readouterr().out.strip().split(" ", 1)
    assert timestamp.endswith("Z")
    assert rest == "info server_started port=8888"


def test_console_access_log_shows_only_fields(capsys):
    configure_logging("INFO", "console")

    structlog.get_logger("tornado.access").info(
        "request", method="GET", path="/api/health", status=304
    )

    _, rest = capsys.readouterr().out.strip().split(" ", 1)
    assert rest == "info method=GET path=/api/health status=304"


def test_console_prints_traceback_after_line(capsys):
    configure_logging("INFO", "console")

    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("tornado.application").exception("handler failed")

    first, *traceback = capsys.readouterr().out.splitlines()
    assert first.endswith("error handler failed")
    assert traceback[-1] == "ValueError: boom"


def test_console_colors_only_the_level():
    render = _make_plain_renderer(colors=True)

    line = render(
        None, "warning", {"timestamp": "T", "level": "warning", "event": "slow"}
    )

    assert line == "T \033[33mwarning\033[0m slow"


def test_console_has_no_colors_when_not_a_terminal(capsys):
    configure_logging("INFO", "console")

    structlog.get_logger().error("boom")

    assert "\033[" not in capsys.readouterr().out
