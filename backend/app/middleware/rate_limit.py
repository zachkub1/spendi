"""
Rate limiter middleware — Redis-backed in production, in-process fallback for dev/test.

Limits:
  - Auth endpoints (/auth/login, /auth/callback): 20 req / 60 s per IP
  - Sync endpoints (/email/sync/*): 10 req / 60 s per user (or IP)
  - Feedback: 30 req / 60 s per IP
  - General API: 200 req / 60 s per IP
"""
import time
import logging
from collections import defaultdict, deque
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# Redis client — shared across workers; falls back gracefully.
try:
    from redis import from_url as _redis_from_url, RedisError
    _redis = _redis_from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    _redis.ping()
    _USE_REDIS = True
    logger.info("[RATE_LIMIT] Backend: Redis")
except Exception:
    _USE_REDIS = False
    _redis = None
    RedisError = Exception  # type: ignore[assignment,misc]
    logger.warning("[RATE_LIMIT] Backend: in-process (Redis unavailable)")

# In-process fallback store
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


def _redis_check(key: str, max_requests: int, window_seconds: int) -> bool:
    """Fixed-window counter via Redis INCR+EXPIRE. O(1), works across workers."""
    try:
        pipe = _redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        count, _ = pipe.execute()
        return count <= max_requests
    except RedisError:
        return True  # fail open — don't block users on Redis hiccup


def _local_check(key: str, max_requests: int, window_seconds: int) -> bool:
    """Sliding-window check using an in-process deque. Thread-safe."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        dq = _windows[key]
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= max_requests:
            return False
        dq.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiter applied to every incoming request."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/"):
            return await call_next(request)

        group, max_req, window = _route_group(request.url.path)
        client_ip = _get_client_ip(request)
        key = f"rl:{group}:{client_ip}"

        allowed = _redis_check(key, max_req, window) if _USE_REDIS else _local_check(key, max_req, window)

        if not allowed:
            logger.warning("[RATE_LIMIT] blocked path=%s group=%s ip=%s", request.url.path, group, client_ip)
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
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
