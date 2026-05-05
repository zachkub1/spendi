"""
In-process sliding-window rate limiter middleware.

Limits:
  - Auth endpoints (/auth/login, /auth/callback): 20 req / 60 s per IP
  - Sync endpoints (/email/sync/*): 10 req / 60 s per user (or IP)
  - General API: 200 req / 60 s per IP

For production with multiple workers, swap the in-process store for Redis
(use redis-py with INCR + EXPIRE, or the `limits` library with RedisStorage).
"""
import time
import logging
from collections import defaultdict, deque
from threading import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# (ip_or_key, route_group) -> deque of timestamps
_windows: dict = defaultdict(deque)
_lock = Lock()


def _route_group(path: str) -> tuple[str, int, int]:
    """Return (group_name, max_requests, window_seconds) for a path."""
    if path.startswith("/auth/login") or path.startswith("/auth/callback"):
        return "auth", 20, 60
    if path.startswith("/email/sync"):
        return "sync", 10, 60
    if path.startswith("/feedback"):
        return "feedback", 30, 60
    return "general", 200, 60


def _check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """
    Sliding window check. Returns True if the request is allowed.
    Thread-safe for single-process deployments.
    """
    now = time.monotonic()
    cutoff = now - window_seconds

    with _lock:
        dq = _windows[key]
        # evict old timestamps
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= max_requests:
            return False
        dq.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter applied to every incoming request."""

    async def dispatch(self, request: Request, call_next):
        # Health checks bypass rate limiting
        if request.url.path in ("/health", "/"):
            return await call_next(request)

        group, max_req, window = _route_group(request.url.path)
        client_ip = _get_client_ip(request)
        key = f"{group}:{client_ip}"

        if not _check_rate_limit(key, max_req, window):
            logger.warning(
                "[RATE_LIMIT] %s blocked: group=%s ip=%s", request.url.path, group, client_ip
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": str(window)},
            )

        return await call_next(request)


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For when behind a trusted proxy."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
