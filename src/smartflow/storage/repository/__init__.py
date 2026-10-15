"""Repositories: the only code that builds SQL queries.

Each one wraps the request's session. They ``flush`` (send the SQL, get ids
back) but never ``commit``: the handler's ``session_maker.begin()`` commits once
at the end, so a request that fails halfway leaves the database unchanged.
"""
