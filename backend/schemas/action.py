from typing import Union, Any, Optional, Annotated
import operator
from typing_extensions import TypedDict
from enum import Enum
from pydantic import BaseModel, Field, root_validator, ValidationError
from conf import settings


class ActionType(str, Enum):
    """
    Enumeration of supported LLM actions.
    """
    write = "write"
    summarize = "summarize"
    translate_ = "translate"


class WriteParams(BaseModel):
    """
    Parameters for the 'write' action.
    """
    write_type: str = Field(..., alias="writeType",
                            description="Desired writing style")
    write_tone: str = Field(..., alias="writeTone",
                            description="Desired writing tone")

    class Config:
        populate_by_name = True


class SummarizeParams(BaseModel):
    """
    Parameters for the 'summarize' action.
    """
    summarize_style: str = Field(..., alias="summarizeStyle",
                                 description="Summary style (e.g., bullet points)")

    class Config:
        populate_by_name = True


class TranslateParams(BaseModel):
    """
    Parameters for the 'translate' action.
    """
    translate_from: str = Field(..., alias="translateFrom",
                                description="Source language code")
    translate_to: str = Field(..., alias="translateTo",
                              description="Target language code")

    class Config:
        populate_by_name = True


class ActionRequest(BaseModel):
    """
    Request model for invoking an LLM action.

    JSON shape:
    {
      "action": "translate",
      "text": "...",
      "parameters": { ... }
    }
    """
    action: ActionType = Field(..., alias="action",
                               description="Which action to perform")

    text: str = Field(..., alias="text", description="The text to process")

    parameters: Union[WriteParams, SummarizeParams, TranslateParams] = Field(
        ..., alias="parameters", description="Parameters for the action"
    )

    model_name: str = Field(
        default=settings.LLM_MODEL_NAME,
        alias="modelName",
        description="Name of the model used for the workflow"
    )

    user_id: str = Field(
        default="",
        alias="userId",
        description="User ID for tracking purposes"
    )

    session_id: str = Field(
        default="",
        alias="sessionId",
        description="Session ID for tracking purposes"
    )

    metadata: dict = Field(
        default={},
        alias="metadata",
        description="Additional metadata for store in langfuse"
    )

    @root_validator(pre=True)
    def validate_and_instantiate_params(cls, values: Any) -> Any:
        """
        Based on the 'action' field, validate 'parameters' against the correct Params model.
        """
        actions = {
            ActionType.write.value: WriteParams,
            ActionType.summarize.value: SummarizeParams,
            ActionType.translate_.value: TranslateParams
        }

        action = values.get("action")
        raw_params = values.get("parameters", {})
        try:

            if action in actions:
                # Dynamically instantiate the correct parameters model
                param_model = actions[action]
                values["parameters"] = param_model(**raw_params)
            else:
                raise ValueError(f"Unsupported action type: {action}")
        except ValidationError as e:
            raise ValueError(
                f"Invalid parameters for action '{action}': {e}"
            ) from e
        return values

    class Config:
        populate_by_name = True
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "action": "translate",
                "text": "Hello, how are you today?",
                "parameters": {
                    "translateFrom": "en",
                    "translateTo": "es"
                },
                "metadata": {}
            }
        }


class ActionInputState(TypedDict):
    parameters: dict
    text: str
    stream_handler: Any
    model_name: str
    run_id: Optional[str]
    session_id: Optional[str]
    user_id: Optional[str]


class ActionOutputState(TypedDict):
    answer: Annotated[str, operator.add]
    run_id: Optional[str]
    session_id: Optional[str]
    user_id: Optional[str]


class ActionResponse(BaseModel):
    """
    Response model for the action invocation.
    """
    answer: str = Field(..., alias="answer", description="The processed text")
    run_id: Optional[str] = Field(
        default=None,
        alias="runId",
        description="Run ID for tracking purposes"
    )
    session_id: Optional[str] = Field(
        default=None,
        alias="sessionId",
        description="Session ID for tracking purposes"
    )
    user_id: Optional[str] = Field(
        default=None,
        alias="userId",
        description="User ID for tracking purposes"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "answer": "Hola, ¿cómo estás hoy?",
                "runId": "12345",
                "sessionId": "67890",
                "userId": "user_123"
            }
        }
