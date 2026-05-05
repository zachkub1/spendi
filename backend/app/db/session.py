from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/spendi")

# Production-grade connection pool settings
_pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
_max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
_pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
_pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # recycle every 30 min

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_timeout=_pool_timeout,
    pool_recycle=_pool_recycle,
    pool_pre_ping=True,  # verify connection health before use
    echo=os.getenv("ENVIRONMENT") == "development",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Database session dependency for FastAPI.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
