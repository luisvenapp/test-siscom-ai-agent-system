from typing import List, Annotated, Optional, Any
from pydantic import BaseModel, Field, RootModel
from schemas.message import Message

class RoomsCreated(BaseModel):
    """
    Model representing the rooms created by the agent.

    Attributes:
        rooms_created (AgentInfo): Information about the created rooms.
        topic (str): The topic for which suggestions are being generated.
    """

    room_id: str = Field(
        default="",
        alias="room_id",
        description="ID of the room created by the agent"
    )

    room_name: str = Field(
        default="",
        alias="room_name",
        description="Name of the room created by the agent"
    )

    room_description: str = Field(
        default="",
        alias="room_description",
        description="Description of the room created by the agent"
    )

    room_topics: List[str] = Field(
        default=[],
        alias="room_topics",
        description="List of topics associated with the room"
    )
    
    

    class Config:
        populate_by_name = True
class RoomSuggestionsRequest(BaseModel):
    """
    Request model to invoke a workflow with a list of messages and the model name.

    Attributes:
        messages (List[Message]): A list of Message objects that drive the workflow. Must contain at least one message.
        model_name (str): The name of the model used, provided by settings.
    """
    room_id: str = Field(
        default="687513d1a1dcc364cc3ed8eb",
        alias="room_id",
        description="Name of the chat"
    )
    rooms_created: List[RoomsCreated]
    
    previous_rooms: Optional[List[str]] = Field(
        default=None,
        alias="previous_rooms",
        description="List of previously created rooms"
    )

    historical_messages: Annotated[
        List[Message],
        Field(
            min_items=1,
            alias="historical_messages",
            description="List of messages for the workflow (must contain at least one message)",
            
        )
    ]
    
    is_last: bool = Field(
        default=False,
        alias="is_last",
        description="Indicates if this is the last suggestion"
    )

    uuid: str = Field(
        default="e481947b-5ee4-4638-bb18-084aad507a0f",
        alias="uuid",
        description="UUID for tracking purposes"
    )
    
    metadata: dict = Field(
        default={},
        alias="metadata",
        description="Additional metadata for store in langfuse"
    )

    class Config:
        populate_by_name = True
        
        
class RoleCreationWizardRequest(BaseModel):
    """
    Request model to invoke a workflow for creating a role creation wizard.

    Attributes:
        user_query (str): The user's query for creating a new assistant.
        uuid (str): The UUID for tracking purposes.
        metadata (dict): Additional metadata for store in langfuse.
    """
    user_query: str = Field(
        default="Quiero crear un asistente que me ayude a gestionar mi agenda y recordatorios.",
        alias="user_query",
        description="User's query for creating a new assistant"
    )
    
    uuid: str = Field(
        default="e481947b-5ee4-4638-bb18-084aad507a0f",
        alias="uuid",
        description="UUID for tracking purposes"
    )
    
    metadata: dict = Field(
        default={},
        alias="metadata",
        description="Additional metadata for store in langfuse"
    )

    class Config:
        populate_by_name = True

