"""``/api/health``: a cheap liveness check for the host (Render, Docker)."""

from smartflow.handlers.base import BaseHandler


class HealthHandler(BaseHandler):
    """Report that the server is up."""

    async def get(self):
        """Return ``{"status": "ok"}``. It doesn't query the database, so it stays fast."""
        self.write({"status": "ok"})
