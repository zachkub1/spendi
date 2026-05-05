"""
Pydantic schemas for the Feedback API.
Validation lives here; sanitization lives in FeedbackService.
"""
from pydantic import BaseModel, Field, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.db.models import FeedbackType

MAX_MESSAGE_LEN = 5_000
MAX_EXAMPLE_LEN = 10_000


class FeedbackCreate(BaseModel):
    type: FeedbackType
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LEN)
    transaction_example: Optional[str] = Field(None, max_length=MAX_EXAMPLE_LEN)

    @model_validator(mode="after")
    def require_example_for_classification(self) -> "FeedbackCreate":
        if (
            self.type == FeedbackType.CLASSIFICATION_ISSUE
            and not self.transaction_example
        ):
            raise ValueError(
                "transaction_example is required for classification_issue feedback"
            )
        return self

    model_config = {"use_enum_values": True}


class FeedbackResponse(BaseModel):
    id: UUID
    type: FeedbackType
    message: str
    created_at: datetime

    model_config = {"from_attributes": True, "use_enum_values": True}
