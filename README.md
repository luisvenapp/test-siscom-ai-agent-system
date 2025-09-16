# **FastAPI LangGraph LLM Service**

## **Overview**

This project provides a high-performance **LLM-based assistant API** powered by **FastAPI, LangGraph, and LiteLLM**. The service is designed for:

- **Invoking AI workflows with structured graphs** using LangGraph.

- **Seamless integration with multiple LLMs** (OpenAI, Cohere, Gemini, Mistral, etc.) via LiteLLM.

- **Session-based conversational memory** for better contextual responses.

- **Support for synchronous and WebSocket-based streaming responses**.

- **Optimized performance** with configurable logging and model selection.

## **Local Development Setup**

### **Prerequisites**

- Python 3.10+

- Docker and Docker Compose

### **Instructions**

1. **Clone the repository:**

   ```
   git clone <repository-url>
   cd siscom-app-ai-agent

   ```

2. **Configure Environment Variables:**
   Create a `.env` file for environment variables. You can copy the existing `docker-compose.prod.yml` environment section as a template. Ensure you have the necessary keys and credentials.

3. **Run the development environment:**
   The `deploy-dev.sh` script simplifies starting the development environment. It uses `docker-compose.yml` to build and run the containers.

   ```
   ./deploy-dev.sh

   ```

   This will start the application container along with a Redpanda instance for messaging.

## **Environment Variables**

To configure the service, set the following environment variables in your `.env` file.

| Variable                                | Description                                  | Default                                                     |
| --------------------------------------- | -------------------------------------------- | ----------------------------------------------------------- |
| `DEBUG`                                 | Enables or disables debug mode.              | `true`                                                      |
| `CORS_ALLOW_ORIGINS`                    | Specifies allowed origins for CORS.          | `*`                                                         |
| `CORS_ALLOW_CREDENTIALS`                | Enables or disables CORS credentials.        | `True`                                                      |
| `CORS_ALLOW_METHODS`                    | Specifies allowed HTTP methods for CORS.     | `*`                                                         |
| `CORS_ALLOW_HEADERS`                    | Specifies allowed headers for CORS.          | `*`                                                         |
| `USE_FILE_LOG`                          | Enables or disables logging to a file.       | `true`                                                      |
| `DEFAULT_LOG_LEVEL`                     | Sets the default logging level.              | `INFO`                                                      |
| `DISABLE_JSON_LOGGING`                  | Disables structured JSON logging.            | `true`                                                      |
| `LLM_DATABASE_POSTGRES_HOST`            | Host for the PostgreSQL LLM database.        | `10.10.40.31`                                               |
| `LLM_DATABASE_POSTGRES_PORT`            | Port for the PostgreSQL database.            | `5432`                                                      |
| `LLM_DATABASE_POSTGRES_USER`            | Username for the PostgreSQL database.        | `usr_dev_scrap`                                             |
| `LLM_DATABASE_POSTGRES_PASSWORD`        | Password for the PostgreSQL database.        | _(Required)_                                                |
| `LLM_DATABASE_VECTOR_STORE_POSTGRES_DB` | PostgreSQL database name for vector storage. | `dev_scrapping_db`                                          |
| `LLM_MODEL_NAME`                        | The LLM model to be used.                    | `deepseek/deepseek-chat`                                    |
| `DEEPSEEK_API_KEY`                      | API key for the DeepSeek model.              | _(Required)_                                                |
| `OLLAMA_API_BASE`                       | Base URL for the Ollama API.                 | `http://10.10.20.25:11434`                                  |
| `LANGFUSE_PUBLIC_KEY`                   | Public key for Langfuse tracing.             | _(Required)_                                                |
| `LANGFUSE_SECRET_KEY`                   | Secret key for Langfuse tracing.             | _(Required)_                                                |
| `LANGFUSE_HOST`                         | Host URL for Langfuse.                       | `https://us.cloud.langfuse.com`                             |
| `LANGFUSE_DEBUG`                        | Enables or disables Langfuse debug mode.     | `True`                                                      |
| `LANGFUSE_LABEL`                        | Label for Langfuse traces.                   | `latest`                                                    |
| `HOSTED_VLLM_API_BASE`                  | Base URL for the hosted vLLM API.            | `http://P-VEGEPRDALLM02.nlt.local:8000/v1`                  |
| `KAFKA_ENABLED`                         | Enables or disables Kafka messaging.         | `true`                                                      |
| `KAFKA_AGENT_TOPIC`                     | Kafka topic for agent chat messages.         | `agent-chat`                                                |
| `KAFKA_AGENT_RESPONSE_TOPIC`            | Kafka topic for agent responses.             | `agent-chat-response`                                       |
| `KAFKA_ANALYTICS_TOPIC`                 | Kafka topic for analytics suggestions.       | `analytics-topic-suggestions`                               |
| `KAFKA_BROKER_URL`                      | URL for the Kafka message broker.            | `localhost:9092`                                            |
| `AUTHORIZATION_TOKEN`                   | Authorization token for webhooks.            | `test`                                                      |
| `WEBHOOK_URL`                           | Webhook URL for agent responses.             | `https://api-siscom.appzone.dev/api/chat/agent/response`    |
| `WEBHOOK_URL_INFO`                      | Webhook URL for agent info.                  | `https://api-siscom.appzone.dev/api/chat/agent/info`        |
| `WEBHOOK_URL_ROOM_SUGGESTION`           | Webhook URL for room suggestions.            | `https://api-siscom.appzone.dev/api/chat/agent/suggestions` |
| `WEBHOOK_BEARER_TOKEN`                  | Bearer token for webhooks.                   | _(Required)_                                                |
| `SERPER_API_KEY`                        | API key for the Serper search service.       | _(Required)_                                                |
| `PORT`                                  | Port for the FastAPI service to run on.      | `8002`                                                      |

## **Production Deployment**

The production deployment is managed via Docker Compose, ensuring a reproducible and scalable environment. The architecture consists of the main application container running two processes managed by `supervisord`: the Uvicorn web server and a background consumer worker.

### **Key Deployment Files**

- **`Dockerfile`**: A multi-stage `Dockerfile` that builds a lean production image. It installs dependencies, sets up a non-root user, and copies the application code.

- **`docker-compose.prod.yml`**: Defines the production services, including the main application (`app`) and the Redpanda message broker. It manages networking, volumes for data persistence (like the Hugging Face cache), and resource limits.

- **`supervisord.conf`**: Configures `supervisord` to run and manage the Uvicorn server and the `agent_consumer.py` script as separate processes within the same container. This is crucial for running the background worker alongside the API.

- **`entrypoint.sh`**: This script is the container's entry point and is responsible for starting the `supervisord` daemon.

### **Deployment Steps**

1. **Prerequisites:**

   - Ensure Docker and Docker Compose are installed on the production server.

   - An `.env` file containing all required production environment variables must be present in the root directory. The `environment` section in `docker-compose.prod.yml` lists all required variables.

2. **Deploy or Update the Service:**
   To deploy the application for the first time or to apply updates (e.g., after pulling new code changes), run the following command from the project's root directory on the instance:

   ```
   docker compose -f docker-compose.prod.yml up -d --no-deps --build

   ```

   - **`docker compose -f docker-compose.prod.yml`**: Specifies the production configuration file.

   - **`up -d`**: Starts the services in detached (background) mode.

   - **`--build`**: Forces Docker to rebuild the application image using the `Dockerfile`. This is essential for applying any code or dependency changes.

   - **`--no-deps`**: Prevents Docker Compose from recreating dependencies (like the database, if it were defined in the same file). It ensures that only the `app` service is rebuilt and restarted.

3. **Verify the Deployment:**
   Check the status of the running containers to ensure everything started correctly.

   ```
   docker compose -f docker-compose.prod.yml ps

   ```

   You can also view the logs for the application and the consumer to check for errors:

   ```
   # View logs for the main app container (includes both uvicorn and consumer)
   docker logs sisscom-app-prod

   # To follow the logs in real-time
   docker logs -f sisscom-app-prod

   ```

## **Testing the API**

### **Swagger UI**

Once the application is running, the API documentation is available at:
`http://10.10.40.12:8001/api/docs`
