from unittest.mock import Mock

import pytest
from pydantic import SecretStr
from tornado.httputil import HTTPHeaders, HTTPServerRequest
from tornado.web import Application, HTTPError

from smartflow.handlers.pm_base_handler import PMHandler

PM_KEY = "s3cret-pm-key"


def make_handler(authorization: str | None, pm_api_key: str | None = PM_KEY):
    headers = HTTPHeaders()
    if authorization is not None:
        headers["Authorization"] = authorization
    request = HTTPServerRequest(
        method="GET", uri="/api/pm", headers=headers, connection=Mock()
    )
    return PMHandler(
        Application(),
        request,
        session_maker=None,
        pm_api_key=SecretStr(pm_api_key) if pm_api_key is not None else None,
    )


@pytest.mark.parametrize(
    "authorization",
    [f"Bearer {PM_KEY}", f"bearer {PM_KEY}", f"BEARER {PM_KEY}"],
)
def test_correct_key_identifies_a_pm(authorization):
    assert make_handler(authorization).get_current_user() == "pm"


@pytest.mark.parametrize(
    "authorization",
    [
        None,  # no header at all
        "",
        "Bearer",  # scheme without a key
        "Bearer wrong-key",
        f"Bearer {PM_KEY.upper()}",  # keys are case-sensitive
        f"Bearer {PM_KEY} extra",
        f"Basic {PM_KEY}",  # wrong scheme
        PM_KEY,  # key without a scheme
    ],
)
def test_anything_else_is_not_a_pm(authorization):
    assert make_handler(authorization).get_current_user() is None


def test_prepare_rejects_missing_credentials_with_401():
    with pytest.raises(HTTPError) as exc_info:
        make_handler(authorization=None).prepare()

    assert exc_info.value.status_code == 401


def test_prepare_rejects_wrong_key_with_401():
    with pytest.raises(HTTPError) as exc_info:
        make_handler("Bearer wrong-key").prepare()

    assert exc_info.value.status_code == 401


def test_prepare_lets_a_pm_through():
    make_handler(f"Bearer {PM_KEY}").prepare()  # no exception


def test_pm_endpoints_are_closed_when_no_key_is_configured():
    # Even a request with a key: without server configuration, nobody is a PM,
    # and the response says so (503) rather than blaming the credentials (401).
    with pytest.raises(HTTPError) as exc_info:
        make_handler(f"Bearer {PM_KEY}", pm_api_key=None).prepare()

    assert exc_info.value.status_code == 503
