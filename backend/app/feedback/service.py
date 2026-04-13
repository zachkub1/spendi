"""
FeedbackService — business logic for creating and storing feedback.

Security responsibilities:
  - Sanitize text: strip HTML/JS tags before persistence
  - Detect and log suspicious payloads (XSS probes, SQLi attempts)
  - All DB writes go through SQLAlchemy ORM (parameterized queries, no raw SQL)
"""
import re
import html
import logging
from sqlalchemy.orm import Session

from app.db.models import Feedback, User
from .schemas import FeedbackCreate

logger = logging.getLogger(__name__)

# ── Suspicious-payload patterns (log only — never silently drop feedback) ─────
_SUSPICIOUS = [
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=\s*[\"']", re.IGNORECASE),   # onclick=, onerror=, …
    re.compile(r"union\s+select", re.IGNORECASE),        # SQLi
    re.compile(r"drop\s+table", re.IGNORECASE),
    re.compile(r";\s*--", re.IGNORECASE),                # SQL comment terminator
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
]


def _sanitize(text: str) -> str:
    """Strip HTML tags, decode entities, collapse whitespace."""
    text = re.sub(r"<[^>]+>", "", text)   # strip tags
    text = html.unescape(text)             # decode &amp; &lt; etc.
    return text.strip()


def _flag_if_suspicious(text: str, user_id: str, field: str) -> None:
    """Log a warning if the text contains known malicious patterns."""
    for pattern in _SUSPICIOUS:
        if pattern.search(text):
            logger.warning(
                "[FEEDBACK] Suspicious payload detected | user_id=%s field=%s "
                "pattern=%r preview=%r",
                user_id,
                field,
                pattern.pattern,
                text[:120],
            )
            break  # one warning per field is enough


class FeedbackService:
    @staticmethod
    def create(db: Session, user: User, payload: FeedbackCreate) -> Feedback:
        user_id_str = str(user.id)

        # Sanitize all text fields
        message = _sanitize(payload.message)
        transaction_example = (
            _sanitize(payload.transaction_example)
            if payload.transaction_example
            else None
        )

        # Log suspicious inputs (we still store them — blocking is too aggressive
        # and classification examples may legitimately contain HTML snippets)
        _flag_if_suspicious(message, user_id_str, "message")
        if transaction_example:
            _flag_if_suspicious(transaction_example, user_id_str, "transaction_example")

        if not message:
            # Edge case: the entire message was HTML markup with no text content
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="Message resolved to empty after sanitization.")

        record = Feedback(
            user_id=user.id,
            type=payload.type,
            message=message,
            transaction_example=transaction_example,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(
            "[FEEDBACK] Submitted | user_id=%s type=%s id=%s",
            user_id_str,
            payload.type,
            record.id,
        )
        return record
