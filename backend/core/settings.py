"""
Configuration settings loaded from environment variables
for the Siscom App GenAI Agent.
"""

import os
from pathlib import Path

from utils import bool_from_str, get_env

# -----------------------------------------------------------------------------
# Base project settings
# -----------------------------------------------------------------------------
DEBUG: bool = bool_from_str(get_env("DEBUG", "t"))

BASE_DIR: Path = Path(__file__).resolve().parent.parent

PROJECT_NAME: str = get_env("PROJECT_NAME", "Siscom App GenAI Agent")
PROJECT_DESCRIPTION: str = get_env(
    "PROJECT_DESCRIPTION",
    (
        "Siscom App GenAI Agent is a powerful tool for generating "
        "responses to user queries using a large language model (LLM)."
    ),
)
PROJECT_VERSION: str = get_env("PROJECT_VERSION", "0.1.0")

AUTHORIZATION_TOKEN: str = get_env("AUTHORIZATION_TOKEN", "")

OPENAPI_URL: str = get_env("OPENAPI_URL", "/api/openapi.json")
DOCS_URL: str = get_env("DOCS_URL", "/api/docs")
REDOC_URL: str = get_env("REDOC_URL", "/api/redoc")


# -----------------------------------------------------------------------------
# Telemetry and logging
# -----------------------------------------------------------------------------
USE_FILE_LOG: bool = bool_from_str(get_env("USE_FILE_LOG", "f"))

LOG_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | <cyan>{name}</cyan>:"
    "<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

DEFAULT_LOG_LEVEL: str = get_env("DEFAULT_LOG_LEVEL", "INFO")

PROMETHEUS_MULTIPROC_DIR: str = get_env(
    "PROMETHEUS_MULTIPROC_DIR", "/tmp"
)
DISABLE_JSON_LOGGING: bool = bool_from_str(
    get_env("DISABLE_JSON_LOGGING", "true")
)


# -----------------------------------------------------------------------------
# LLM model settings
# -----------------------------------------------------------------------------
LLM_MODEL_NAME: str = get_env("LLM_MODEL_NAME", "deepseek/deepseek-chat")

# Database selection for LLM storage
DEFAULT_LLM_DATABASE: str = get_env(
    "DEFAULT_LLM_DATABASE", "postgresql"
)

MAX_TOKEN_LENGTH: int = int(get_env("MAX_TOKEN_LENGTH", "25000"))


# -----------------------------------------------------------------------------
# PostgreSQL configuration for vector store
# -----------------------------------------------------------------------------
LLM_DATABASE_POSTGRES_HOST: str = get_env(
    "LLM_DATABASE_POSTGRES_HOST", "localhost"
)
LLM_DATABASE_POSTGRES_READ_PORT: int = int(
    get_env("LLM_DATABASE_POSTGRES_READ_PORT", "5432")
)
LLM_DATABASE_POSTGRES_WRITE_PORT: int = int(
    get_env("LLM_DATABASE_POSTGRES_WRITE_PORT", "5432")
)
LLM_DATABASE_POSTGRES_USER: str = get_env(
    "LLM_DATABASE_POSTGRES_USER", "postgres"
)
LLM_DATABASE_POSTGRES_PASSWORD: str = get_env(
    "LLM_DATABASE_POSTGRES_PASSWORD", "postgres"
)
LLM_DATABASE_VECTOR_STORE_POSTGRES_DB: str = get_env(
    "LLM_DATABASE_VECTOR_STORE_POSTGRES_DB", "llm"
)
LLM_DATABASE_POSTGRES_VECTOR_COLLECTION: str = get_env(
    "LLM_DATABASE_POSTGRES_VECTOR_COLLECTION",
    "webscrapping",
)

EMBEDDING_NAME: str = get_env(
    "EMBEDDING_NAME", "sentence-transformers/all-mpnet-base-v2"
)


# -----------------------------------------------------------------------------
# Langfuse integration settings
# -----------------------------------------------------------------------------
LANGFUSE_PUBLIC_KEY: str = get_env("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY: str = get_env("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST: str = get_env(
    "LANGFUSE_HOST", "https://us.cloud.langfuse.com"
)

# Enable Langfuse only if both public and secret keys are provided
LANGFUSE_IS_ENABLE: bool = bool(
    LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
)
LANGFUSE_DEBUG: bool = bool_from_str(get_env("LANGFUSE_DEBUG", "f"))
LANGFUSE_LABEL: str = get_env("LANGFUSE_LABEL", "production")


# -----------------------------------------------------------------------------
# Ensure OpenAI API key is defined
# -----------------------------------------------------------------------------
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "XXX"

LLM_RESPONSE_DELAY: float = float(get_env("LLM_RESPONSE_DELAY", "0.1"))

#
#
#
KAFKA_BROKER_URL: str = get_env("KAFKA_BROKER_URL", "redpanda:9092")
KAFKA_AGENT_TOPIC:str = get_env("KAFKA_AGENT_TOPIC", "agent-chat")
KAFKA_AGENT_RESPONSE_TOPIC:str = get_env("KAFKA_AGENT_RESPONSE_TOPIC", "agent-chat-response")
KAFKA_ANALYTICS_TOPIC: str = get_env("KAFKA_ANALYTICS_TOPIC", "analytics-topic-suggestions")
KAFKA_ROOM_SUGGESTION_TOPIC: str = get_env("KAFKA_ROOM_SUGGESTION_TOPIC", "room-suggestion-topic")

KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "false").lower() == "true"

# Redis
# REDIS_HOST:str = get_env("REDIS_HOST", "localhost")
# REDIS_PORT:str = get_env("REDIS_PORT", "6379")

WEBHOOK_URL: str = get_env("WEBHOOK_URL")
WEBHOOK_URL_INFO: str = get_env("WEBHOOK_URL_INFO", "https://api-siscom.appzone.dev/api/chat/agent/info")
WEBHOOK_URL_ROOM_SUGGESTION: str = get_env("WEBHOOK_URL_ROOM_SUGGESTION", "https://api-siscom.appzone.dev/api/chat/agent/suggestions")
WEBHOOK_BEARER_TOKEN: str = get_env("WEBHOOK_BEARER_TOKEN")

SERPER_API_KEY: str = get_env("SERPER_API_KEY", "")

SISCOM_API_URL: str = get_env("SISCOM_API_URL", "https://api-siscom.appzone.dev/api/chat/agent/info")

PORT: int = int(get_env("PORT", "8002"))