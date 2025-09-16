from pydantic import BaseModel, Field
from typing import List, Optional

class Rules(BaseModel):
    id: str = Field(..., description="Unique identifier for the rule")
    name: str = Field(..., description="Name of the rule")
    description: str = Field(..., description="Description of the rule")

class AgentInfo(BaseModel):
    id: str = Field(..., alias="_id")
    name: str  # Display name or internal reference
    personality: str  # Overall character (e.g., Friendly, Serious)
    dedication: str  # Mission or main responsibility
    qualities: List[str]  # Key traits (e.g., Empathetic, Clear)
    some_more: Optional[str] = None  # Extra personalization
    communication_style: str  # Style of expression (e.g., Conversational)
    language_level: str  # Formal, Neutral, Informal, etc.
    knowledge_scope: str  # Topic boundaries (e.g., Legal, Tech)
    response_frequency: str  # When the agent should speak
    tone: str  # Emotional flavor (e.g., Reassuring, Fun)
    emoji_usage: str  # Level of emoji usage (None, Light, Frequent)
    agent_type: str  # Role type (Mentor, Assistant, etc.)
    country: str  # The country the agent is associated with
    # context_country: str  # Rich cultural/linguistic context

    class Config:
        schema_extra = {
            "example": {
                "id": "agent_01",
                "name": "PanaLegal",
                "personality": "Friendly",
                "dedication": "Answer legal questions",
                "qualities": ["Empathetic", "Clear", "Knowledgeable"],
                "some_more": "Has experience in civil and labor law. Avoids technical jargon when not needed.",
                "communication_style": "Conversational",
                "language_level": "Neutral",
                "knowledge_scope": "Legal matters",
                "response_frequency": "Only when mentioned",
                "tone": "Supportive",
                "emoji_usage": "Light use",
                "agent_type": "Mentor",
                "country": "Venezuela",
                # "context_country": (
                #     "In Venezuela, expressions like 'pana', 'chévere', and 'arrecho' are common. "
                #     "Legal topics often relate to constitutional changes, inflation laws, or labor rights. "
                #     "Be sensitive to political instability and economic concerns."
                # )
            }
        }

class RoomInfoDetails(BaseModel):
    name: str
    description: str
    tags: List[str]
    rules: List[Rules]
    agents_can_interact: Optional[bool] = Field(default=True, description="Indicates if agents can interact with each other in the room")

    class config:
        schema_extra = {
            "example": {
                "name": "Conference Room A",
                "description": "A spacious conference room with a projector and whiteboard.",
                "tags": ["conference", "meeting", "projector"],
                "country": "USA",
                "rules": [
                    {
                        "id": "rule1",
                        "name": "No food or drinks",
                        "description": "Food and drinks are not allowed in the conference room."
                    },
                    {
                        "id": "rule2",
                        "name": "Clean up after use",
                        "description": "Please clean up the room after your meeting."
                    }
                ],
                "agents_can_interact": True
            }
        }


class RoomData(BaseModel):
    room: RoomInfoDetails
    agents: List[AgentInfo]


class ChatInfoResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: RoomData