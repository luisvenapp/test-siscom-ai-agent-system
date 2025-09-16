# import sys
# import os

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import time
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import json
from langfuse.callback import CallbackHandler

from schemas.agent import InvokeWorkflowRequest, TopicSuggestionsRequest
from schemas.suggested_rooms import RoomSuggestionsRequest
from services.agent.multi_agents import MultiAgents
from conf import settings
from core.logging_config import get_logger
import aiohttp

logger = get_logger(__name__)

# Limit the number of concurrent tasks
SEMAPHORE_LIMIT = 10
MAX_WORKFLOW_RETRIES = 3
RETRY_DELAY_SECONDS = 2
WORKFLOW_FAILURE_MESSAGES = (
    "Lo siento, no pude generar una respuesta en este momento.",
    "Agent stopped due to iteration limit or time limit",
    "Lo siento, ocurrió un error interno después de varios intentos",
    "Mensaje enviado al grupo"
)


async def process_chat_message(data: dict, session: aiohttp.ClientSession):
    """Processes a message from the agent chat topic."""
    request = InvokeWorkflowRequest(**data)
    uuid = data.get("uuid", "")

    
    agent = await MultiAgents.create(settings.LLM_MODEL_NAME)
    # Save tracing
    callback_handlers = []
    if settings.LANGFUSE_IS_ENABLE:
        callback_handlers.append(
            CallbackHandler(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
                trace_name="siscom-agent-consumer",
                debug=settings.LANGFUSE_DEBUG,
                metadata=request.metadata if request.metadata else {},
            )
        )

    workflow = agent.create_workflow().compile()

    response = {}
    for attempt in range(MAX_WORKFLOW_RETRIES):
        logger.info(f"Executing chat workflow for {uuid} (Attempt {attempt + 1}/{MAX_WORKFLOW_RETRIES})...", extra={"data": data})
        
        response = await workflow.ainvoke({
            "room_id": request.room_id,
            "messages": request.messages,
            "uui_id": uuid,
        }, config={
            "uui_id": uuid,
            "callbacks": callback_handlers,
            "recursion_limit": 200,
        })

        list_message = response.get("list_message")
        should_retry = False
        if list_message and isinstance(list_message, list) and list_message[0]:
            first_message = list_message[0]
            if any(error_msg in first_message for error_msg in WORKFLOW_FAILURE_MESSAGES):
                should_retry = True

        if not should_retry:
            logger.info(f"Workflow for {uuid} succeeded on attempt {attempt + 1}.")
            break

        logger.warning(f"Workflow for {uuid} failed on attempt {attempt + 1} with message: '{list_message[0]}'. Retrying...")
        if attempt < MAX_WORKFLOW_RETRIES - 1:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
    else:
        logger.error(f"Workflow for {uuid} failed after {MAX_WORKFLOW_RETRIES} attempts. Sending last response.")
        
    
    list_message = response.get("list_message", [])
    
    for i, msg in enumerate(list_message):
        logger.info(f"Message {i + 1}: {msg}")
        
        msg = msg.replace("`", "").strip()
        msg = msg.strip("` \n").removeprefix("json\n")
        msg = msg.replace("**", "").strip()
        
        if len(msg) <= 1:
            logger.warning(f"Message {i + 1} for {uuid} is too short. Skipping.")
            continue
        else:
            if not msg:
                logger.warning(f"Empty message received for {uuid}. Skipping.")
                continue
            
            elif msg[0] == "(" and msg[-1] == ")":
                logger.warning(f"Message {i + 1} for {uuid} is a tuple. Skipping.")
                continue
            
            else:
                # Prepare webhook payload
                payload = {
                    "uuid": uuid,
                    "message": [msg],
                    "user_id": response.get("agent_id_executed", ""),
                    "send_message": True if response.get("agent_id_executed") else False,
                }

                # Send response to backend via webhook
                webhook_url = settings.WEBHOOK_URL
                headers = {
                    "Authorization": f"Bearer {settings.WEBHOOK_BEARER_TOKEN}",
                    "Content-Type": "application/json"
                }

                logger.info(f"Final answer: {payload['message']}.\nUser ID: {payload['user_id']}\nSend Message: {payload['send_message']}\nUUID: {uuid}")

                async with session.post(webhook_url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        logger.info(f"Webhook sent successfully for {uuid}")
                    else:
                        error_text = await resp.text()
                        logger.error(f"Webhook failed for {uuid}: {resp.status} - {error_text}")
                            
                time.sleep(20)  # Small delay to avoid overwhelming the webhook endpoint

async def process_analytics_message(data: dict):
    """Processes a message from the analytics topic."""
    request = TopicSuggestionsRequest(**data)
    uuid = data.get("uuid", "")
    logger.info(f"Processing analytics event for {uuid} from room {request.room_id}")
    
    # TODO: Implement the logic for handling topic suggestions.
    # This could involve another agent, a different workflow, or a direct call to a service.
    # For now, we'll just log it and simulate work.
    
    # Example placeholder:
    # analytics_agent = await AnalyticsAgent.create(settings.LLM_MODEL_NAME)
    # workflow = analytics_agent.create_workflow().compile()
    # response = await workflow.ainvoke(...)
    # await send_result_somewhere(response)
    
    logger.info(f"Analytics event for {uuid} processed (stub).")
    await asyncio.sleep(1) # Simulate work

async def process_room_suggestion_message(data: dict, session: aiohttp.ClientSession):
    """Processes a message from the room suggestion topic."""
    
    # time.sleep(15)  # Small delay to ensure DB consistency if needed
    request = RoomSuggestionsRequest(**data)
    uuid = data.get("uuid", "")
    logger.info(f"Processing room suggestion event for {uuid} from room {request.room_id}")

    try:
        agent = await MultiAgents.create(settings.LLM_MODEL_NAME)
        
        callback_handlers = []
        if settings.LANGFUSE_IS_ENABLE:
            callback_handlers.append(
                CallbackHandler(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                    trace_name="siscom-room-suggestion-consumer",
                    debug=settings.LANGFUSE_DEBUG,
                    metadata=request.metadata if request.metadata else {},
                )
            )

        # First, run the workflow to analyze and store the current room's data
        single_room_workflow = agent.create_room_suggestions_workflow().compile()
        single_room_result = await single_room_workflow.ainvoke({
            "room_id": request.room_id,
            "messages": request.historical_messages,
            "rooms_created": request.rooms_created,
            "previous_rooms": request.previous_rooms
        }, config={
            "uui_id": uuid,
            "callbacks": callback_handlers,
            "recursion_limit": 200,
        })

        if error := single_room_result.get("error"):
            # Log the error for the individual processing step
            logger.error(f"Workflow for single room suggestion {uuid} (room_id: {request.room_id}) failed: {error}")
            # If this was the last one, we should still notify about the failure.
            if request.is_last:
                payload = {
                    "suggestion": {},
                }
                await send_webhook(settings.WEBHOOK_URL_ROOM_SUGGESTION, payload, uuid, session)
        
        # If this is the last message in the batch, run the final analysis workflow
        if request.is_last:
            logger.info(f"Last message received for batch {uuid}. Running final analysis workflow.")
            
            final_analysis_workflow = agent.create_final_room_analysis_workflow().compile()

            # This workflow doesn't need specific inputs as it reads from DB
            final_result = await final_analysis_workflow.ainvoke({"uui_id": uuid})
            

            if error := final_result.get("error"):
                logger.error(f"Final analysis workflow for batch {uuid} failed: {error}")
                payload = {
                    "uuid": uuid,
                    "status": "error",
                    "suggestion": {},
                    "error": error
                }
            else:
                payload = {
                    # "uuid": uuid,
                    # "status": "success",
                    # The final analysis is the main suggestion now
                    "suggestion":  final_result.get("room_suggestion", {}),
                    # "error": None
                }

            logger.info(f"Final room suggestion for batch {uuid}: {payload.get('suggestion')}")
            await send_webhook(settings.WEBHOOK_URL_ROOM_SUGGESTION, payload, uuid, session)
        else:
            logger.info(f"Processed intermediate room suggestion for room_id: {request.room_id}. Waiting for last message.")

    except Exception as e:
        logger.exception(f"Error processing room suggestion for {uuid}: {e}")
        payload = {
            "uuid": uuid,
            "status": "error",
            "suggestion": {},
            "error": f"An unexpected error occurred: {str(e)}"
        }
        await send_webhook(settings.WEBHOOK_URL_ROOM_SUGGESTION, payload, uuid, session)

async def send_webhook(url: str, payload: dict, uuid: str, session: aiohttp.ClientSession):
    """Helper function to send webhook."""
    headers = {
        "Authorization": f"Bearer {settings.WEBHOOK_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    async with session.post(url, json=payload, headers=headers) as resp:
        if resp.status == 200:
            logger.info(f"Webhook sent successfully for {uuid}")
        else:
            error_text = await resp.text()
            logger.error(f"Webhook failed for {uuid}: {resp.status} - {error_text}")

async def process_message(msg, producer, semaphore, session):
    async with semaphore:
        try:
            data = json.loads(msg.value.decode("utf-8"))
            
            if msg.topic == settings.KAFKA_AGENT_TOPIC: await process_chat_message(data, session)
            elif msg.topic == settings.KAFKA_ANALYTICS_TOPIC: await process_analytics_message(data)
            elif msg.topic == settings.KAFKA_ROOM_SUGGESTION_TOPIC: await process_room_suggestion_message(data, session)
            else: logger.warning(f"Received message from unhandled topic: {msg.topic}")

        except Exception as e:
            logger.exception(f"Error while processing message from topic {msg.topic}: {e}")


async def consume():
    topics_to_consume = [
        settings.KAFKA_AGENT_TOPIC,
        settings.KAFKA_ANALYTICS_TOPIC,
        settings.KAFKA_ROOM_SUGGESTION_TOPIC
    ]
    logger.info(f"Starting consumer for topics: {topics_to_consume}")

    consumer = AIOKafkaConsumer(
        *topics_to_consume,
        bootstrap_servers=settings.KAFKA_BROKER_URL,
        group_id="agent-group",
        enable_auto_commit=True,
        auto_offset_reset="latest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BROKER_URL)

    await consumer.start()
    await producer.start()

    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    tasks = set()

    async with aiohttp.ClientSession() as session:
        try:
            async for msg in consumer:
                # Start a background task to process the message
                task = asyncio.create_task(process_message(msg, producer, semaphore, session))
                tasks.add(task)

                # Clean up finished tasks to avoid memory leak
                task.add_done_callback(tasks.discard)

        finally:
            logger.info("Stopping consumer and producer...")
            await consumer.stop()
            await producer.stop()
            await asyncio.gather(*tasks)  # Wait for remaining tasks to complete
            logger.info("All tasks finished. Exiting.")

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user.")
