import json
from fastapi import APIRouter, Body, HTTPException
from aiokafka import AIOKafkaProducer
from core.logging_config import get_logger
from schemas.agent import (
    InvokeWorkflowRequest,
    TopicSuggestionsRequest,
    MessageSuggestionsRequest, 
)
from schemas.suggested_rooms import RoomSuggestionsRequest, RoleCreationWizardRequest
from langfuse.callback import CallbackHandler
import uuid
from langfuse import Langfuse
from services.agent.multi_agents import MultiAgents
from schemas.langfuse import LangfuseReceiveFeedbackRequest, LangfuseReceiveFeedbackResponse
from conf import settings

from aiokafka import AIOKafkaProducer

router = APIRouter(
    tags=["Agent"],
)

logger = get_logger(__name__)

# redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

@router.post("/chat", summary="Invoke Chat Agent Workflow (Kafka)")
async def invoke_chat_workflow(
    request: InvokeWorkflowRequest = Body(...),
) -> dict:
    try:
        uuid_ = request.uuid or str(uuid.uuid4())
        message = request.model_dump()
        message["uuid"] = uuid_

        producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BROKER_URL)
        await producer.start()
        await producer.send_and_wait(
            settings.KAFKA_AGENT_TOPIC,
            json.dumps(message).encode("utf-8")
        )
        await producer.stop()

        return {
            "status": "message_sent",
            "uui_id": uuid_,
            "detail": "Message successfully sent to Kafka for processing"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kafka error: {e}")
    
@router.post("/generate-topic-suggestions", summary="Generate Topic Suggestions")
async def generate_topic_suggestions(
    request: TopicSuggestionsRequest = Body(...)
) -> dict:
    """
    Generates topic suggestions based on the provided conversation history and room details.

    This endpoint invokes a dedicated agent workflow that:
    1. Summarizes the conversation.
    2. Fetches room information.
    3. Generates a list of relevant topic suggestions using an LLM.
    """
    try:
        agent = await MultiAgents.create(settings.LLM_MODEL_NAME)
        workflow = agent.create_suggestions_workflow().compile()

        # The workflow expects 'messages' and 'room_id' in the initial state,
        # which are provided by the TopicSuggestionsRequest schema.
        result = await workflow.ainvoke({
            "room_id": request.room_id,
            "messages": request.historical_messages,
        })

        if error := result.get("error"):
            raise HTTPException(status_code=500, detail=error)

        return {
            "topics": result.get("suggestions", [])
        }
    except Exception as e:
        logger.exception(f"Error generating topic suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating topic suggestions: {e}")
    
@router.post("/generate-message-suggestion", summary="Generate Message Suggestions")
async def generate_message_suggestions(
    request: MessageSuggestionsRequest = Body(...)
) -> dict:
    """
    Generates topic suggestions based on the provided conversation history and room details.

    This endpoint invokes a dedicated agent workflow that:
    1. Summarizes the conversation.
    2. Fetches room information.
    3. Generates a list of relevant topic suggestions using an LLM.
    """
    try:
        agent = await MultiAgents.create(settings.LLM_MODEL_NAME)
        workflow = agent.create_message_suggestions_workflow().compile()
        
        callback_handlers = []

        if settings.LANGFUSE_IS_ENABLE:
            callback_handlers.append(
                CallbackHandler(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                    user_id="",
                    session_id="",
                    trace_name="sisscom-app-ai-agent-generate-message-suggestion",
                    debug=settings.LANGFUSE_DEBUG,
                    metadata={},
                )
            )

        # The workflow expects 'messages' and 'room_id' in the initial state,
        # which are provided by the MessageSuggestionsRequest schema.
        result = await workflow.ainvoke({
            "agent_info": request.agent,
            "topic": request.topic,
        }, config={
            "uui_id": str(uuid.uuid4()),
            "callbacks": callback_handlers,
            "recursion_limit": 200,
        })

        if error := result.get("error"):
            raise HTTPException(status_code=500, detail=error)
        
        final_result = "\n\n".join(result.get("list_message", []))
        
        final_result = final_result.replace("Final Answer:", "").strip()
        
        return {
            "message": final_result
            # "message": "result.get("list_message", "")
        }
    except Exception as e:
        logger.exception(f"Error generating topic suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating topic suggestions: {e}")
    
    
@router.post("/generate-room-suggestion", summary="Generate Room Suggestions (Kafka)")
async def generate_room_suggestions(
    request: RoomSuggestionsRequest = Body(...)
) -> dict:
    """
    Queues a request to generate room suggestions based on conversation history.

    This endpoint sends the request to a Kafka topic for asynchronous processing.
    The result will be sent via a webhook.
    """
    try:
        uuid_ = request.uuid or str(uuid.uuid4())
        message = request.model_dump()
        message["uuid"] = uuid_

        producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BROKER_URL)
        await producer.start()
        await producer.send_and_wait(
            settings.KAFKA_ROOM_SUGGESTION_TOPIC,
            json.dumps(message).encode("utf-8")
        )
        await producer.stop()

        return {
            "status": "request_queued",
            "uuid": uuid_,
            "detail": "Room suggestion request successfully sent to Kafka for processing."
        }
    except Exception as e:
        logger.exception(f"Error sending room suggestion request to Kafka: {e}")
        raise HTTPException(status_code=500, detail=f"Kafka error: {e}")

@router.post("/role-creation-wizard", summary="Generate Role Creation Wizard")
async def generate_role_creation_wizard(
    request: RoleCreationWizardRequest = Body(...)
) -> dict:
    """
    Queues a request to generate room suggestions based on conversation history.

    This endpoint sends the request to a Kafka topic for asynchronous processing.
    The result will be sent via a webhook.
    """
    try:
        agent = await MultiAgents.create(settings.LLM_MODEL_NAME)
        workflow = agent.rule_creation_wizard_workflow().compile()
        
        callback_handlers = []

        if settings.LANGFUSE_IS_ENABLE:
            callback_handlers.append(
                CallbackHandler(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                    user_id="",
                    session_id="",
                    trace_name="sisscom-rule-creation-wizard",
                    debug=settings.LANGFUSE_DEBUG,
                    metadata={},
                )
            )

        # The workflow expects 'messages' and 'room_id' in the initial state,
        # which are provided by the MessageSuggestionsRequest schema.
        result = await workflow.ainvoke({
            "user_query": request.user_query,
        }, config={
            "uui_id": request.uuid or str(uuid.uuid4()),
            "callbacks": callback_handlers,
            "recursion_limit": 200,
        })

        if error := result.get("error"):
            raise HTTPException(status_code=500, detail=error)
        
        
        return {
            "rule": result["answer"]
        }
    except Exception as e:
        logger.exception(f"Error generating topic suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating topic suggestions: {e}")


@router.post(
    "/feedback/{run_id}",
    responses={
        200: {
            "model": LangfuseReceiveFeedbackResponse,
            "description": "Feedback recorded successfully"
        },
    },
    tags=["Agent"],
    summary="Receive feedback for the workflow",
    response_model=dict,
    status_code=200,
)
async def receive_feedback(
    request: LangfuseReceiveFeedbackRequest = Body(...),
    run_id: str = None,
):
    """Receive user feedback on a specific workflow execution."""

    if not settings.LANGFUSE_IS_ENABLE:
        logger.warning("Langfuse is not enabled. Feedback will not be sent.")
        raise HTTPException(
            status_code=503,
            detail="Langfuse is disabled in the current environment. Feedback was not recorded."
        )

    try:
        langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )

        result = langfuse.score(
            name="user-feedback",
            trace_id=run_id,
            value=request.score,
            comment=request.comment,
            metadata=request.metadata,
        )

        # Langfuse might return None if the trace_id doesn't exist or fails silently
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"No trace found for run_id '{run_id}'. Feedback was not recorded."
            )

        return {"message": "Feedback recorded successfully."}

    except Exception as e:
        logger.exception(
            f"Unexpected error while submitting feedback to Langfuse: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while recording feedback. Please try again later."
        )