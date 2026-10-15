"""Business rules, independent of HTTP.

Services take a session and plain values, enforce the rules (does it exist?
was it merged?) and raise domain errors from ``errors.py``. They never commit:
the handler owns the transaction, so one request is all-or-nothing.
"""
