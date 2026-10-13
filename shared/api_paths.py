"""URL prefixes of the JSON API.

``/api/v1/...`` is the versioned API. The unversioned ``/api/...`` paths are
aliases served by the same views, kept for the clients that already use them
(the website, the Telegram bot). See docs/api.md.
"""

API_PREFIX = "/api/"
API_V1_PREFIX = "/api/v1/"


def unversioned(path: str) -> str:
    """``/api/v1/x`` -> ``/api/x``; any other path unchanged."""
    if path.startswith(API_V1_PREFIX):
        return API_PREFIX + path[len(API_V1_PREFIX):]
    return path


def v1_url_prefix(url_prefix: str) -> str:
    """The v1 twin of a blueprint prefix: ``/api/nutrition`` -> ``/api/v1/nutrition``."""
    if not url_prefix.startswith(API_PREFIX):
        raise ValueError(f"not an API prefix: {url_prefix!r}")
    return API_V1_PREFIX + url_prefix[len(API_PREFIX):]
