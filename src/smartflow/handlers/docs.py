from tornado.web import RequestHandler

from smartflow.openapi import build_spec


class OpenAPIHandler(RequestHandler):
    def get(self) -> None:
        self.finish(build_spec())
