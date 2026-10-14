"""One JSON shape for every error answered under /api/.

    {"error": ..., "code": "not_found", "message": "Meal not found"}

- ``code``: stable, machine-readable, snake_case. Clients branch on it.
- ``message``: human-readable English text. Safe to show or log; never an
  exception text, a traceback or anything from the server's internals.
- ``details``: optional object with extra data, only where an endpoint has
  something structured to add.
- ``error``: kept from the formats the endpoints used before, so existing
  clients (the website, the Telegram bot) keep working. It holds whatever the
  endpoint returned there: a code or a message. New clients read ``code`` and
  ``message``.

Endpoints may keep returning their own ``{"error": ...}`` bodies;
``complete_error_body`` adds the missing ``code`` and ``message`` to every
JSON error under /api/, so the shape holds without touching each endpoint.
"""

import re

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

API_PREFIX = "/api/"

DEFAULT_CODES = {
    400: "bad_request",
    401: "authentication_required",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "unprocessable_entity",
    429: "rate_limited",
    500: "internal_server_error",
    503: "service_unavailable",
}

DEFAULT_MESSAGES = {
    "bad_request": "Bad request",
    "authentication_required": "Authentication required",
    "forbidden": "Forbidden",
    "not_found": "Not found",
    "method_not_allowed": "Method not allowed",
    "conflict": "Conflict",
    "payload_too_large": "Payload too large",
    "unsupported_media_type": "Unsupported media type",
    "unprocessable_entity": "Unprocessable entity",
    "rate_limited": "Too many requests. Try again later.",
    "internal_server_error": "Internal server error",
    "service_unavailable": "Service temporarily unavailable",
}

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def is_api_request() -> bool:
    # Every rule under /api/ belongs to the api package (checked by
    # test_architecture), so the path is a reliable test, unlike headers.
    return request.path.startswith(API_PREFIX)


def default_code(status: int) -> str:
    if status in DEFAULT_CODES:
        return DEFAULT_CODES[status]
    return "internal_server_error" if status >= 500 else "bad_request"


def _message_for(code: str) -> str:
    if code in DEFAULT_MESSAGES:
        return DEFAULT_MESSAGES[code]
    text = code.replace("_", " ")
    return text[:1].upper() + text[1:]


def error_body(status: int, code: str | None = None, message: str | None = None, **extra) -> dict:
    """The body of an API error; ``extra`` keeps fields such as ``error``."""
    code = code or default_code(status)
    body = {**extra, "code": code, "message": message or _message_for(code)}
    body.setdefault("error", code)
    return body


def error_response(status: int, code: str | None = None, message: str | None = None, **extra):
    response = jsonify(error_body(status, code, message, **extra))
    response.status_code = status
    return response


def complete_error_body(body: dict, status: int) -> dict:
    """Add ``code`` and ``message`` to an endpoint's own error body."""
    legacy = body.get("error")
    code = body.get("code")
    if not isinstance(code, str) or not code:
        code = legacy if isinstance(legacy, str) and _CODE_RE.match(legacy) else default_code(status)
    message = body.get("message")
    if not isinstance(message, str) or not message:
        if isinstance(legacy, str) and legacy and not _CODE_RE.match(legacy):
            message = legacy
        else:
            message = _message_for(code)
    return {**body, "code": code, "message": message}


def http_error_response(error: HTTPException):
    """JSON for an HTTPException raised under /api/ (abort, bad JSON...)."""
    status = error.code or 500
    code = default_code(status)
    description = error.description
    # Werkzeug's stock descriptions are long and speak of "the browser";
    # an explicit abort(..., description=...) is kept as the message.
    if not description or description == type(error).description:
        message = DEFAULT_MESSAGES.get(code)
    else:
        message = description
    response = error_response(status, code, message, error=description or error.name)
    if status == 405 and getattr(error, "valid_methods", None):
        response.headers["Allow"] = ", ".join(error.valid_methods)
    return response


def _complete_errors(response):
    if response.status_code < 400 or not is_api_request() or not response.is_json:
        return response
    body = response.get_json(silent=True)
    if isinstance(body, dict) and ("error" in body or "code" in body):
        completed = complete_error_body(body, response.status_code)
        if completed != body:
            response.set_data(jsonify(completed).get_data())
    return response


def init_api_errors(app) -> None:
    app.after_request(_complete_errors)
