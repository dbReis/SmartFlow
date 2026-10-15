"""``/openapi.json``: the API's OpenAPI spec, for tools and the UI's client."""

from tornado.web import RequestHandler

from smartflow.openapi import build_spec


class OpenAPIHandler(RequestHandler):
    """Serve the spec. A plain RequestHandler: it needs no database session."""

    def get(self) -> None:
        """Return the OpenAPI document as JSON."""
        self.finish(build_spec())
