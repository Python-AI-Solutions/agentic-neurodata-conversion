"""Rate limiting middleware for API endpoints.

Simple in-memory rate limiter with configurable limits for standard
and LLM-heavy endpoints.
"""

import logging
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 60  # requests
RATE_LIMIT_WINDOW = 60  # seconds (60 requests per minute)
RATE_LIMIT_LLM_REQUESTS = 10  # LLM-heavy endpoints
RATE_LIMIT_LLM_WINDOW = 60  # seconds (10 LLM calls per minute)


class SimpleRateLimiter:
    """Simple in-memory rate limiter for MVP."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit.

        Args:
            client_id: Unique identifier for client (IP address)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Remove old requests outside the window
            self._requests[client_id] = [req_time for req_time in self._requests[client_id] if req_time > cutoff]

            # Check if under limit
            if len(self._requests[client_id]) < max_requests:
                self._requests[client_id].append(now)
                return True

            return False

    def get_retry_after(self, client_id: str, window_seconds: int) -> int:
        """Get seconds until rate limit resets."""
        with self._lock:
            if not self._requests[client_id]:
                return 0
            oldest_request = min(self._requests[client_id])
            return max(0, int(window_seconds - (time.time() - oldest_request)))


# Global rate limiter instance
_rate_limiter = SimpleRateLimiter()


def check_rate_limit(request: Request, max_requests: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW):
    """Check rate limit for incoming request.

    Raises HTTPException 429 if rate limit exceeded.
    """
    # Use client IP as identifier (with X-Forwarded-For support for proxies)
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    if not _rate_limiter.is_allowed(client_ip, max_requests, window):
        retry_after = _rate_limiter.get_retry_after(client_ip, window)
        logger.warning(f"Rate limit exceeded for {client_ip}. Retry after {retry_after}s")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


async def rate_limit_llm(request: Request):
    """Rate limiting dependency for LLM-heavy endpoints (stricter limits)."""
    check_rate_limit(request, RATE_LIMIT_LLM_REQUESTS, RATE_LIMIT_LLM_WINDOW)
