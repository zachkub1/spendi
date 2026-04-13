"""
Feedback routes.

POST /feedback  — authenticated users only; rejects with 401 otherwise.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from .schemas import FeedbackCreate, FeedbackResponse
from .service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])

# Hard cap: 64 KB per request (prevents memory exhaustion from huge payloads)
_MAX_BODY_BYTES = 64 * 1024


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
)
async def submit_feedback(
    request: Request,
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """
    Submit a bug report, suggestion, or transaction classification issue.

    - Requires a valid Bearer token (401 if missing/invalid).
    - message is required and must be non-empty after sanitization.
    - transaction_example is required when type = classification_issue.
    - All inputs are sanitized (HTML stripped) before persistence.
    """
    content_length = int(request.headers.get("content-length", 0))
    if content_length > _MAX_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request body exceeds the {_MAX_BODY_BYTES // 1024} KB limit.",
        )

    return FeedbackService.create(db, current_user, payload)
