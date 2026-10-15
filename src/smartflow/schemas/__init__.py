"""Pydantic DTOs: what the API accepts and returns.

Naming: `…Create` models validate request bodies (`extra="forbid"` turns
unknown fields into a 422 instead of silently ignoring a typo); `…Out` models
shape responses and read straight from ORM objects (`from_attributes=True`).
Keeping them apart from the SQLAlchemy models means the API contract doesn't
change when the tables do.
"""
