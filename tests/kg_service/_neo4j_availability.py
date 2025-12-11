"""Neo4j availability helpers for integration tests.

These helpers intentionally probe the running service (HTTP/Bolt) rather than
using "is a password set" as a proxy for availability.
"""

from __future__ import annotations

import urllib.request


def neo4j_http_available(port: int, *, timeout_s: float = 2.0) -> bool:
    """Return True if Neo4j HTTP endpoint responds on localhost."""
    try:
        with urllib.request.urlopen(  # nosec B310 - localhost probe in tests
            f"http://localhost:{port}",
            timeout=timeout_s,
        ) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False

