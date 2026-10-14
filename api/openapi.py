"""OpenAPI 3.1 description of the JSON API, built from the app itself.

- paths, methods and path parameters: the URL map (the /api/v1 rules);
- query parameters: the views' own ``request.args.get(...)`` calls, read
  from their source, including one level of module helpers;
- authentication, summaries and bodies: api/openapi_docs.py.

docs/openapi.json is the committed output of ``python -m web.scripts.openapi``.
web/tests/unit/test_openapi.py fails when it no longer matches the routes,
and checks the documented bodies against real responses.
"""

import ast
import inspect
import re
import textwrap

from api.openapi_docs import AUTH_BY_BLUEPRINT, DEFAULT_AUTH, OPERATIONS, SCHEMAS, TAGS
from shared.api_paths import API_V1_PREFIX
from shared.bot_signature import HEADER_NONCE, HEADER_SIGNATURE, HEADER_TIMESTAMP

V1_SUFFIX = "_v1"
SERVER_URL = API_V1_PREFIX.rstrip("/")
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_CONVERTER_SCHEMAS = {
    "int": {"type": "integer", "minimum": 0, "maximum": 2**31 - 1},
    "float": {"type": "number"},
    "path": {"type": "string"},
    "default": {"type": "string"},
}
_ARG_TYPES = {"int": {"type": "integer"}, "float": {"type": "number"}}

ERROR = {"$ref": "#/components/schemas/Error"}


def _error_response(description):
    return {"description": description, "content": {"application/json": {"schema": ERROR}}}


ERROR_RESPONSES = {
    400: _error_response("Invalid request (code names the problem, message explains it)."),
    401: _error_response("Not signed in (code: authentication_required), or a bad bot signature."),
    403: _error_response("Forbidden: cross-site request, premium only, or not open to a Telegram session."),
    404: _error_response("Not found."),
    405: _error_response("Method not allowed."),
    409: _error_response("Conflict."),
    413: _error_response("Request body too large."),
    429: _error_response("Too many requests (code: rate_limited)."),
    500: _error_response("Unexpected server error (code: internal_server_error)."),
    503: _error_response("A service the operation needs is unavailable."),
}


# --- Reading the views ---------------------------------------------------------------


def _unwrap(func):
    while hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    return func


def _function_tree(func):
    try:
        source = textwrap.dedent(inspect.getsource(func))
    except (OSError, TypeError):
        return None
    return ast.parse(source)


def _is_args_get(node):
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "get"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "args"
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "request"
    )


def _arg_type(call):
    for keyword in call.keywords:
        if keyword.arg == "type" and isinstance(keyword.value, ast.Name):
            return _ARG_TYPES.get(keyword.value.id)
    return None


def _query_params_of(func, depth=1, bound=None):
    """{name: schema} for request.args.get(...) in ``func`` and, ``depth``
    levels down, the module functions it calls. ``bound`` maps a helper's
    parameter names to the constants the caller passed."""
    tree = _function_tree(func)
    if tree is None:
        return {}
    bound = bound or {}
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_args_get(node) and node.args:
            name = node.args[0]
            if isinstance(name, ast.Constant) and isinstance(name.value, str):
                found.setdefault(name.value, _arg_type(node) or {"type": "string"})
            elif isinstance(name, ast.Name) and name.id in bound:
                found.setdefault(bound[name.id], _arg_type(node) or {"type": "string"})
        elif depth and isinstance(node.func, ast.Name):
            helper = func.__globals__.get(node.func.id)
            if inspect.isfunction(helper) and helper.__module__ == func.__module__:
                params = list(inspect.signature(helper).parameters)
                passed = {
                    params[i]: arg.value
                    for i, arg in enumerate(node.args[: len(params)])
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                }
                for key, schema in _query_params_of(helper, depth - 1, passed).items():
                    found.setdefault(key, schema)
    return found


def _rate_limited(func):
    tree = _function_tree(func)
    if tree is None:
        return False
    names = {
        node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    return bool(names & {"hit_limit", "too_many_requests"})


# --- Building the description --------------------------------------------------------


def _openapi_path(rule):
    path = rule.rule[len(SERVER_URL):]
    return re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", path)


def _path_parameters(rule):
    params = []
    for converter, _arguments, name in _parse_rule(rule.rule):
        params.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": dict(_CONVERTER_SCHEMAS.get(converter or "default", {"type": "string"})),
            }
        )
    return params


def _parse_rule(rule):
    for match in re.finditer(r"<(?:(\w+)(?:\(([^)]*)\))?:)?(\w+)>", rule):
        yield match.group(1), match.group(2), match.group(3)


def _security(auth):
    if auth == "session":
        return [{"session": []}]
    if auth == "bot":
        return [{"botSignature": [], "botTimestamp": [], "botNonce": []}]
    return []


def _operation(app, rule, method):
    endpoint = rule.endpoint
    blueprint, _, view_name = endpoint.rpartition(".")
    legacy_blueprint = blueprint[: -len(V1_SUFFIX)] if blueprint.endswith(V1_SUFFIX) else blueprint
    legacy_endpoint = f"{legacy_blueprint}.{view_name}"
    doc = OPERATIONS.get(legacy_endpoint, {})
    view = _unwrap(app.view_functions[endpoint])
    auth = doc.get("auth") or AUTH_BY_BLUEPRINT.get(legacy_blueprint, DEFAULT_AUTH)

    operation = {
        "operationId": legacy_endpoint,
        "tags": [TAGS[legacy_blueprint]],
        "security": _security(auth),
        "x-auth": auth,
    }
    summary = doc.get("summary") or (inspect.getdoc(view) or "").split("\n")[0].strip()
    if summary:
        operation["summary"] = summary

    parameters = _path_parameters(rule)
    required_query = set(doc.get("required_query", ()))
    for name, schema in sorted(_query_params_of(view).items()):
        parameters.append({"name": name, "in": "query", "required": name in required_query, "schema": schema})
    if parameters:
        operation["parameters"] = parameters

    if method in WRITE_METHODS:
        body = doc.get("request")
        operation["requestBody"] = {
            "required": False,
            "content": {
                "application/json": {
                    "schema": body or {"type": "object", "description": "Not described yet."}
                }
            },
        }

    status = doc.get("status", 200)
    if "response" in doc:
        success = {"description": "Success.", "content": {"application/json": {"schema": doc["response"]}}}
    else:
        success = {
            "description": "Success. The body is not described yet.",
            "content": {"application/json": {"schema": {}}},
        }
    responses = {str(status): success}

    codes = set(doc.get("errors", ()))
    codes.add(500)
    if auth == "session":
        codes.add(401)
        if method in WRITE_METHODS:
            codes.add(403)
    if auth == "bot":
        codes.update({400, 401, 413, 429})
    if any(converter == "int" for converter, _, _ in _parse_rule(rule.rule)):
        codes.add(404)
    if _rate_limited(view):
        codes.add(429)
    for code in sorted(codes):
        responses[str(code)] = {"$ref": f"#/components/responses/Error{code}"}
    operation["responses"] = responses
    return operation


def _info():
    return {
        "title": "NosiFit API",
        "version": "1",
        "description": (
            "JSON API of NosiFit (nutrition, training, recovery, the Telegram bot). "
            f"Paths are relative to {SERVER_URL}. The same operations answer under the "
            "unversioned /api prefix for existing clients. Errors always have the Error "
            "shape. See docs/api.md for versioning, errors and authentication."
        ),
    }


def build_spec(app):
    paths = {}
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, sorted(r.methods))):
        if not rule.rule.startswith(API_V1_PREFIX):
            continue
        item = paths.setdefault(_openapi_path(rule), {})
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            item[method.lower()] = _operation(app, rule, method)

    return {
        "openapi": "3.1.0",
        "info": _info(),
        "servers": [{"url": SERVER_URL}],
        "tags": [{"name": name} for name in sorted(set(TAGS.values()))],
        "paths": paths,
        "components": {
            "schemas": SCHEMAS,
            "responses": {f"Error{code}": response for code, response in sorted(ERROR_RESPONSES.items())},
            "securitySchemes": {
                "session": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session",
                    "description": (
                        "Session cookie from signing in on the website, or from "
                        "POST /telegram/login for the Telegram bot. Writes from browsers "
                        "must be same-origin (Origin / Referer are checked)."
                    ),
                },
                "botSignature": {
                    "type": "apiKey",
                    "in": "header",
                    "name": HEADER_SIGNATURE,
                    "description": (
                        "HMAC-SHA256 over method, path, timestamp, nonce and body with "
                        "the bot's shared secret (shared/bot_signature.py). Only the "
                        "NosiFit Telegram bot has the secret."
                    ),
                },
                "botTimestamp": {"type": "apiKey", "in": "header", "name": HEADER_TIMESTAMP},
                "botNonce": {"type": "apiKey", "in": "header", "name": HEADER_NONCE},
            },
        },
    }
