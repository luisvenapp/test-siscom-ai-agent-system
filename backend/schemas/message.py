from enum import Enum
from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    role: Role = Field(..., description="system, user, or assistant")
    sender: str = Field(..., description="Name of the person sending the message")
    content: str = Field(..., description="Text content of the message.")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "12345",
                "role": "user",
                "sender": "John Doe",
                "content": "Hello, how can I help you?"
            }
        }
