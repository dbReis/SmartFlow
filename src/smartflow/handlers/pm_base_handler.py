import hmac

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tornado.web import HTTPError

from smartflow.handlers.base import BaseHandler


class PMHandler(BaseHandler):
    def initialize(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        pm_api_key: SecretStr | None,
    ) -> None:
        super().initialize(session_maker)
        self.pm_api_key = pm_api_key

    def get_current_user(self) -> str | None:
        scheme, _, token = self.request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token or self.pm_api_key is None:
            return None
        expected = self.pm_api_key.get_secret_value()
        if hmac.compare_digest(token.encode(), expected.encode()):
            return "pm"
        return None

    def prepare(self) -> None:
        super().prepare()
        if self.pm_api_key is None:
            raise HTTPError(503, reason="PM features are not configured")
        if self.current_user is None:
            raise HTTPError(401, reason="Invalid or missing credentials")
