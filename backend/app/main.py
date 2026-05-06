import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth.routes import router as auth_router
from app.email_ingest.routes import router as email_router
from app.transactions.routes import router as transactions_router
from app.transactions.p2p_routes import router as p2p_router
from app.feedback.routes import router as feedback_router
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Spendi API",
    description="Privacy-first personal finance tracker",
    version="0.1.0",
    # Disable Swagger/ReDoc in production to reduce attack surface
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)

# ── Middleware (applied in reverse order) ──────────────────────────────────────

# 1. Rate limiting — outermost so it runs first
app.add_middleware(RateLimitMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. CORS — restrict to known frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=600,
)


# ── Request ID + latency logging ───────────────────────────────────────────────

@app.middleware("http")
async def request_logging(request: Request, call_next):
    import uuid
    request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "method=%s path=%s status=%d duration_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ── Startup / shutdown ─────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Spendi API — environment=%s", settings.ENVIRONMENT)
    if settings.ENVIRONMENT == "production":
        try:
            settings.validate()
            logger.info("Configuration validation passed")
        except ValueError as e:
            logger.critical("FATAL: Configuration validation failed: %s", e)
            raise


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check — used by ALB / ECS health checks."""
    return {"status": "ok", "service": "spendi-api"}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Spendi API", "version": "0.1.0"}


app.include_router(auth_router)
app.include_router(email_router)
app.include_router(transactions_router)
app.include_router(p2p_router)
app.include_router(feedback_router)
