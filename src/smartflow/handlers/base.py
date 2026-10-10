from sqlalchemy import text
from tornado.web import RequestHandler


class TesteHandler(RequestHandler):
    def initialize(self, session_maker):
        self.session_maker = session_maker

    async def get(self):
        async with self.session_maker() as session:
            # database ops - To do later, this is only here to test the session maker and if the database connection to neon is working properly
            await session.execute(text("SELECT 1"))
        self.write({"status": "ok"})
