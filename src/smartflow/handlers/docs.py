"""API documentation served by the app: /docs (Swagger UI) and /openapi.json."""

from tornado.web import RequestHandler

from smartflow.openapi import build_spec, swagger_html


class SwaggerUIHandler(RequestHandler):
    def get(self) -> None:
        self.set_header("Content-Type", "text/html; charset=utf-8")
        self.finish(swagger_html("/openapi.json"))


class OpenAPIHandler(RequestHandler):
    def get(self) -> None:
        # "Try it out" calls the same server that served the spec.
        self.finish(build_spec(f"{self.request.protocol}://{self.request.host}"))
