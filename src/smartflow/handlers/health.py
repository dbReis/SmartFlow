from smartflow.handlers.base import BaseHandler


class HealthHandler(BaseHandler):
    async def get(self):
        self.write({"status": "ok"})
