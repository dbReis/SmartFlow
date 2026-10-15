"""Product Manager handlers: endpoints that require the PM key.

PMs authenticate with one shared key, sent as ``Authorization: Bearer <key>``.
It is a deliberate simplification for this project; per-user accounts (JWT)
would replace it later without changing the handlers.
"""

import hmac

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler


class PMHandler(BaseHandler):
    """Base for PM endpoints: rejects requests without a valid PM key.

    Attributes:
        public_methods: HTTP methods anyone may call on this endpoint, e.g.
            ``("GET",)`` so the UI can list categories while only PMs create them.
    """

    public_methods: tuple[str, ...] = ()

    def initialize(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        pm_api_key: SecretStr | None,
    ) -> None:
        """Store the session factory and the PM key from make_app()'s pm_deps.

        Args:
            session_maker: Factory that opens one database session per request.
            pm_api_key: The configured PM key, or None if PM features are off.
        """
        super().initialize(session_maker)
        self.pm_api_key = pm_api_key

    def get_current_user(self) -> str | None:
        """Identify the caller from the Authorization header.

        Tornado calls this lazily the first time ``self.current_user`` is read.
        The scheme is case-insensitive ("bearer" works); the key is not.

        Returns:
            "pm" if the request carries the right key, otherwise None.
        """
        scheme, _, token = self.request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token or self.pm_api_key is None:
            return None
        expected = self.pm_api_key.get_secret_value()
        # Constant-time comparison: the response time doesn't reveal how many
        # leading characters of a guessed key were right.
        if hmac.compare_digest(token.encode(), expected.encode()):
            return "pm"
        return None

    def prepare(self) -> None:
        """Check access before the request reaches get()/post()/put().

        Order matters: a server without a PM key answers 503 for everyone, so
        a client can tell "not configured" apart from "wrong key" (401).

        Raises:
            HTTPError: 503 if no PM key is configured; 401 if the key is
                missing or wrong.
        """
        super().prepare()
        if self.request.method in self.public_methods:
            return
        if self.pm_api_key is None:
            raise HTTPError(503, reason="PM features are not configured")
        if self.current_user is None:
            raise HTTPError(401, reason="Invalid or missing credentials")


class PMSessionHandler(PMHandler):
    """``/api/pm/session``: lets the UI check a PM key before using it."""

    def get(self) -> None:
        """Answer 204 No Content; reaching this method means the key is valid."""
        self.set_status(204)
        self.finish()
