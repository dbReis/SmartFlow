from smartflow.handlers.base import BaseHandler


class HealthHandler(BaseHandler):
    # BaseHandler, not RequestHandler: browsers on other origins (the UI) need
    # its CORS headers here too.
    async def get(self):
        self.write({"status": "ok"})
