from __future__ import annotations
import os
import json
from conf import settings
import asyncio
from asyncio import Future
from aiokafka import AIOKafkaConsumer
from core.logging_config import get_logger
from core.metrics_config import setup_metrics
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from middlewares import (
    add_process_time_header,
    exception_handler,
    validation_exception_handler,
)
from utils.healthcheck import (
    HealthCheckFactory,
    healthCheckRoute,
)
from fastapi.exceptions import RequestValidationError
from utils.healthcheck.model import HealthCheckModel
from utils.shared_state import pending_responses
import warnings
from controllers import (
    agent
)


warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="pydantic"
)


def set_middlewares(app: FastAPI) -> FastAPI:
    """
    Set middlewares for the FastAPI application.

    :param app: FastAPI application.

    :return: FastAPI application with middlewares.

    """

    app.add_middleware(CORSMiddleware, **settings.CORS_SETTINGS)
    logger.debug("Middleware added")

    app.middleware("http")(add_process_time_header)
    logger.debug("Process time Middleware added")

    app.add_exception_handler(
        Exception,
        exception_handler
    )
    logger.debug("Exception handler added")

    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler
    )
    logger.debug("Validation exception handler added")

    return app


def import_routes(app: FastAPI) -> FastAPI:

    app.include_router(agent.router, prefix="/v1")
    # app.include_router(context.router, prefix="/v1")
    return app

async def response_listener():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_AGENT_RESPONSE_TOPIC,
        bootstrap_servers=settings.KAFKA_BROKER_URL,
        group_id="response-group",
        auto_offset_reset="latest"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                logger.info(f"KAFKA_BROKER_URL: {settings.KAFKA_BROKER_URL}")
                uui_id = data.get("uui_id")
                logger.info(f"run id: {uui_id}")
                logger.info(f"pending_responses: {pending_responses}")
                
                if uui_id and uui_id in pending_responses:
                    future = pending_responses.pop(uui_id)
                    if not future.done():
                        future.set_result(data)

            except Exception as e:
                logger.error(f"Error procesando respuesta: {e}")
    finally:
        await consumer.stop()


def get_application(logger) -> FastAPI:
    """
    Returns a FastAPI application.

    :return: FastAPI application.
    """
    logger.info("Creating FastAPI application")
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.PROJECT_VERSION,
        openapi_url=settings.OPENAPI_URL,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
    )
    logger.debug("FastAPI application created")

    app = set_middlewares(app)

    app = import_routes(app)

    _healthChecks = HealthCheckFactory()
    app.add_api_route(
        "/api/health/",
        tags=["Health Check"],
        endpoint=healthCheckRoute(factory=_healthChecks),
        response_model=HealthCheckModel,
    )
    app.add_api_route(
        "/api/health",
        tags=["Health Check"],
        endpoint=healthCheckRoute(factory=_healthChecks),
        include_in_schema=False,
    )

    return app


os.environ.setdefault("FASTAPI_CONFIG", "core.settings")
logger = get_logger(__name__)

app = get_application(logger)
setup_metrics(app)

logger.info("FastAPI application created")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(response_listener())
    logger.info("🚀 Kafka response listener iniciado")
logger.info("Telelemetry initialized")
