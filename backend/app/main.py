from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.auth.routes import router as auth_router
from app.email_ingest.routes import router as email_router
from app.transactions.routes import router as transactions_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Ledgerly API",
    description="Privacy-first personal finance tracker with automated email ingestion",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    logger.info(f"Starting Ledgerly API in {settings.ENVIRONMENT} mode")

    # Validate configuration in production
    if settings.ENVIRONMENT == "production":
        try:
            settings.validate()
            logger.info("Configuration validation passed")
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "service": "ledgerly-api",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Ledgerly API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# Include routers
app.include_router(auth_router)
app.include_router(email_router)
app.include_router(transactions_router)