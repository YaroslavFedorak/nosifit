"""Responses shared by the API route modules."""

from flask import jsonify


def too_many_requests(message="Too many requests. Try again later."):
    """429 for API routes; the same body web.app.security sends to /api/ paths."""
    response = jsonify({"error": message, "code": "rate_limited"})
    response.status_code = 429
    return response
