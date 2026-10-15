"""HTTP layer: one Tornado handler per route.

Handlers parse and validate the request, call a service, and turn domain
errors into HTTP status codes. Business rules live in ``smartflow.services``.
"""
