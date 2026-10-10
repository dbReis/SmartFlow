from tornado.web import RequestHandler


class HealthHandler(RequestHandler):
    async def get(self):
        self.write({"status": "ok"})
