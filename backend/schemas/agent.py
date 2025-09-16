from typing import List, Annotated, Optional, Any
from enum import Enum
import operator
from litellm import ConfigDict
from pydantic import BaseModel, Field, RootModel
from typing_extensions import TypedDict
from schemas.message import Message
from schemas.room_info import RoomData, AgentInfo
from schemas.slang import SlangAnalysis
from schemas.suggested_rooms import RoomsCreated
from conf import settings


class InvokeWorkflowRequest(BaseModel):
    """
    Request model to invoke a workflow with a list of messages and the model name.

    Attributes:
        messages (List[Message]): A list of Message objects that drive the workflow. Must contain at least one message.
        model_name (str): The name of the model used, provided by settings.
    """

    room_id: str = Field(
        default="",
        alias="room_id",
        description="Name of the chat"
    )

    messages: Annotated[
        List[Message],
        Field(
            min_items=1,
            alias="messages",
            description="List of messages for the workflow (must contain at least one message)"
        )
    ]

    uuid: str = Field(
        default="e481947b-5ee4-4638-bb18-084aad507a0f",
        alias="uuid",
        description="uui ID for tracking purposes"
    )

    metadata: dict = Field(
        default={},
        alias="metadata",
        description="Additional metadata for store in langfuse"
    )

    class Config:
        populate_by_name = True


class StreamingDataTypeEnum(Enum):
    TEXT = "text"
    LLM = "llm"
    APPENDIX = "appendix"
    ACTION = "action"
    SIGNAL = "signal"


class StreamingSignalsEnum(Enum):
    RETRIEVER = "RETRIEVER"
    START = "START"
    END = "END"
    TOOL_END = "TOOL_END"
    LLM_END = "LLM_END"


class SSEResponse(BaseModel):
    data: str
    dataType: StreamingDataTypeEnum = StreamingDataTypeEnum.TEXT
    metadata: dict[
        str,
        Any,
    ] = {}


class SSEStreamResponseSchema(RootModel[List[SSEResponse]]):
    """
    RootModel para documentar un stream de mensajes SSE,
    representado internamente como una lista de SSEMessage.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": [
                {"data": "START",    "data_type": "signal", "metadata": {}},
                {"data": "**",       "data_type": "llm",    "metadata": {}},
                {"data": "AI",       "data_type": "llm",    "metadata": {}},
                {"data": "LLM_END",  "data_type": "signal", "metadata": {}},
                {
                    "data": "END",
                    "data_type": "signal",
                    "metadata": {
                        "question": "Hello, what's AI?",
                        "conversation_summary": "",
                        "additional_context": "\\n\\n",
                        "chat_name": "TechTalks",
                        "chat_description": "Aquí hablamos de todo lo que mueve el mundo tech: software, hardware, inteligencia artificial y más.",
                        "topics": ["tecnología"],
                        "user_id": "",
                        "session_id": "",
                        "run_id": "1cdbff5b-2ca3-4c81-8314-2f6525499475"
                    }
                }
            ]
        }
    )


class InputState(TypedDict):
    stream_handler: Any
    messages: List[Message]
    question: str
    conversation_summary: str
    room_id: str
    uui_id: Optional[str]
    agent_name: Optional[str]
    group_context: Optional[str]
    room_details: Optional[RoomData]
    latest_news_summary: Optional[str]
    question_answer_summary: Optional[str]
    next_node: Optional[str]
    personalize_agent: Optional[dict]
    validation_retries: Optional[int]
    slang_context: Optional[List[SlangAnalysis]]  # Context from slang analysis
    answer: Annotated[str, operator.add]
    agent_info: Optional[AgentInfo]
    topic: Optional[str]
    personalize_retries: Optional[int]
    personalize_failed: Optional[bool]
    frequent_words: Optional[dict]
    frequent_emojis: Optional[dict]
    frequent_hashtags: Optional[dict]
    rooms_created: Optional[List[RoomsCreated]]
    previous_rooms: Optional[List[str]]
    mentioned_users: Optional[dict]
    main_topics_group: Optional[List[str]]
    room_suggestion: Optional[dict]
    final_analysis: Optional[dict]
    error: Optional[str]
    user_query: Optional[str]
    answer: Optional[str]


class OutputState(TypedDict):
    # answer: Annotated[str, operator.add]
    answer: Optional[str]
    run_id: Optional[str]
    session_id: Optional[str]
    agent_id_executed: Optional[str]
    list_message: Optional[List[str]]
    suggestions: Optional[List[str]]
    room_suggestion: Optional[dict]
    final_analysis: Optional[dict]
    error: Optional[str]

class ChatResponseSchema(BaseModel):
    answer: str
    room_id: str
    uui_id: str
    session_id: str
    user_id: str
    send_message: bool = Field(
        default=True,
        description="Indicates whether the response should be sent as a message in the chat."
    )
    
    

class TopicSuggestionsRequest(BaseModel):
    """
    Request model to invoke a workflow with a list of messages and the model name.

    Attributes:
        messages (List[Message]): A list of Message objects that drive the workflow. Must contain at least one message.
        model_name (str): The name of the model used, provided by settings.
    """

    room_id: str = Field(
        default="",
        alias="room_id",
        description="Name of the chat"
    )

    historical_messages: Annotated[
        List[Message],
        Field(
            min_items=1,
            alias="historical_messages",
            description="List of messages for the workflow (must contain at least one message)"
        )
    ]

    uuid: str = Field(
        default="e481947b-5ee4-4638-bb18-084aad507a0f",
        alias="uuid",
        description="uui ID for tracking purposes"
    )

    metadata: dict = Field(
        default={},
        alias="metadata",
        description="Additional metadata for store in langfuse"
    )

    class Config:
        populate_by_name = True
        
        
class MessageSuggestionsRequest(BaseModel):
    """
    Request model to invoke a workflow with a list of messages and the model name.

    Attributes:
        messages (List[Message]): A list of Message objects that drive the workflow. Must contain at least one message.
        model_name (str): The name of the model used, provided by settings.
    """

    agent: AgentInfo
    topic: str = Field(
        default="",
        alias="topic",
        description="Topic for which suggestions are being generated"
    )

    class Config:
        populate_by_name = True
        