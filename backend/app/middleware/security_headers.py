"""
Security headers middleware.
Adds OWASP-recommended HTTP security headers to every response.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers on every outbound response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent browsers from MIME-sniffing the content type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Disallow framing entirely (clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # Block reflected XSS in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Strict Transport Security — force HTTPS for 1 year (only in production)
        from app.config import settings
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Referrer policy — don't leak URL to third parties
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — deny access to sensitive browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # Content-Security-Policy for the API (JSON only, no scripts served)
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        # Remove server banner
        response.headers.pop("server", None)
        response.headers.pop("x-powered-by", None)

        return response
