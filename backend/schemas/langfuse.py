from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LangfuseReceiveFeedbackRequest(BaseModel):
    """
    Payload for receiving feedback via Langfuse.

    Attributes:
        score: Feedback score (0 = bad, 1 = good).
        comment: Optional comment accompanying the feedback.
        metadata: Optional additional metadata for context.
    """
    score: int = Field(
        ...,
        description="Feedback score (0 = bad, 1 = good)",
    )
    comment: Optional[str] = Field(
        None,
        description="Optional comment for feedback",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata for feedback",
    )

    class Config:
        """
        Pydantic model configuration for request schema.
        """
        json_schema_extra = {
            "example": {
                "score": 1,
                "comment": "Great job!",
            }
        }


class LangfuseReceiveFeedbackResponse(BaseModel):
    """
    Response indicating feedback recording status.

    Attributes:
        message: Confirmation message for feedback submission.
    """
    message: str = Field(
        ...,
        description=(
            "Response message indicating feedback was "
            "recorded successfully"
        ),
    )

    class Config:
        """
        Pydantic model configuration for response schema.
        """
        json_schema_extra = {
            "example": {
                "message": "Feedback recorded successfully.",
            }
        }
