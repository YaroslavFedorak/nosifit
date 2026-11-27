"""Rate-limit identity of the client making the current request.

Shared by the web pages and the JSON API (re-exported by web.app.security).
"""

import ipaddress

from flask import request


def client_ip() -> str:
    """Rate-limit identity of the client.

    ProxyFix already replaced remote_addr with the proxy-reported client.
    IPv6 is grouped by /64: one customer usually gets a whole /64, so
    counting single addresses would let them rotate through 2**64 of them.
    """
    raw = request.remote_addr or "unknown"
    try:
        address = ipaddress.ip_address(raw)
    except ValueError:
        return raw
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped:
            return str(address.ipv4_mapped)
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)
