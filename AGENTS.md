# Repository Guidelines

## Project Structure & Module Organization

The codebase is organized into three main directories: `backend/` contains the core FastAPI application with controllers, services, and agent workflows; `tests-cualfication-llm/` houses a comprehensive LLM testing and evaluation framework; and `scripts/` provides development utilities for environment setup and local execution.

## Build, Test, and Development Commands

```bash
# Setup development environment
./scripts/configure.sh

# Start development server (with auto-reload)
./scripts/start.sh

# Production deployment
docker compose up -d --build

# Run LLM qualification tests
cd tests-cualfication-llm && python -m src.main
```

## Coding Style & Naming Conventions

- **Indentation**: 4 spaces (Python standard)
- **File naming**: snake_case for Python files, kebab-case for configs
- **Function/variable naming**: snake_case following PEP 8
- **Async patterns**: Extensive use of async/await for I/O operations
- **Linting**: Standard Python conventions, loguru for structured logging

## Testing Guidelines

- **Framework**: Custom LLM testing framework in `tests-cualfication-llm/`
- **Test files**: Located in `tests-cualfication-llm/scenarios/` as JSON configurations
- **Running tests**: Execute orchestrator from `tests-cualfication-llm/src/`
- **Coverage**: Focuses on LLM response quality, accuracy, and performance metrics

## Commit & Pull Request Guidelines

- **Commit format**: Descriptive messages (e.g., "Gemini Benchmarking", "Phase 1 Checked")
- **PR process**: Standard review process with focus on agent workflow integrity
- **Branch naming**: Feature-based branching recommended for agent modifications

---

# Repository Tour

## 🎯 What This Repository Does

**test-siscom-ai-agent-system** is a high-performance LLM-based assistant API that provides intelligent conversational agents with structured workflow orchestration, multi-model support, and real-time processing capabilities for enterprise chat systems.

**Key responsibilities:**
- Orchestrate complex AI workflows using LangGraph for contextual conversations
- Process chat messages asynchronously via Kafka with webhook integrations
- Generate intelligent topic and message suggestions based on conversation analysis
- Provide multi-LLM support through LiteLLM (OpenAI, Cohere, Gemini, Mistral, etc.)

---

## 🏗️ Architecture Overview

### System Context
```
[External Chat System] → [FastAPI] → [Kafka Topics] → [Agent Workers]
                            ↓              ↓              ↓
                      [PostgreSQL] ← [LangGraph] → [Webhooks]
                      [Vector Store]   [Workflows]   [Responses]
```

### Key Components
- **MultiAgents** - Orchestrates LangGraph workflows for different conversation types
- **Agent Workers** - Background Kafka consumers that process chat messages asynchronously
- **LLM Manager** - Abstraction layer for multiple language models via LiteLLM
- **Vector Store** - PostgreSQL-based document retrieval for contextual responses
- **Webhook System** - Real-time response delivery to external chat platforms

### Data Flow
1. **Request Reception** - FastAPI receives chat requests and queues them in Kafka topics
2. **Workflow Execution** - Background workers execute LangGraph workflows with agent nodes
3. **Context Retrieval** - Vector store provides relevant documents and conversation history
4. **Response Generation** - LLM generates contextual responses through structured workflows
5. **Delivery** - Results sent via webhooks to external systems with retry mechanisms

---

## 📁 Project Structure [Partial Directory Tree]

```
test-siscom-ai-agent-system/
├── backend/                    # Main FastAPI application
│   ├── controllers/           # API route handlers
│   ├── services/              # Business logic and agent orchestration
│   │   ├── agent/            # LangGraph workflows and nodes
│   │   │   ├── nodes/        # Individual agent capabilities
│   │   │   └── tools/        # Agent tools (search, analysis)
│   │   └── llm_manager.py    # Multi-model LLM abstraction
│   ├── core/                 # Configuration and logging
│   ├── workers/              # Background Kafka consumers
│   ├── schemas/              # Pydantic data models
│   └── main.py               # FastAPI application entry point
├── tests-cualfication-llm/    # LLM testing and evaluation framework
│   ├── src/                  # Testing orchestration system
│   ├── scenarios/            # Test scenarios and cases
│   └── reports/              # Test results and metrics
├── scripts/                   # Development utilities
└── docker-compose.yml        # Production deployment configuration
```

### Key Files to Know

| File | Purpose | When You'd Touch It |
|------|---------|---------------------|
| `backend/main.py` | FastAPI application entry point | Adding new routes/middleware |
| `backend/services/agent/multi_agents.py` | Workflow orchestration | Creating new agent workflows |
| `backend/workers/agent_consumer.py` | Kafka message processing | Modifying async processing logic |
| `backend/core/settings.py` | Environment configuration | Adding new config variables |
| `requirements.txt` | Python dependencies | Adding new libraries |
| `docker-compose.yml` | Production deployment | Changing deployment configuration |
| `supervisord.conf` | Process management | Modifying service startup |

---

## 🔧 Technology Stack

### Core Technologies
- **Language:** Python 3.10+ - Chosen for AI/ML ecosystem compatibility and async capabilities
- **Framework:** FastAPI - High-performance async API framework with automatic OpenAPI docs
- **AI Orchestration:** LangGraph - Structured workflow management for complex agent interactions
- **LLM Integration:** LiteLLM - Unified interface for multiple language model providers

### Key Libraries
- **aiokafka** - Asynchronous Kafka client for message queue processing
- **langchain-postgres** - PostgreSQL vector store integration for document retrieval
- **langfuse** - LLM observability and tracing for workflow monitoring
- **nemoguardrails** - Content safety and guardrails for AI responses

### Development Tools
- **uvicorn** - ASGI server for FastAPI development and production
- **supervisord** - Process management for multi-service containers
- **loguru** - Structured logging with JSON output support

---

## 🌐 External Dependencies

### Required Services
- **PostgreSQL** - Vector database for document storage and retrieval (critical for context)
- **Kafka/Redpanda** - Message broker for asynchronous workflow processing (critical for scaling)
- **LLM APIs** - External model providers (OpenAI, Cohere, Gemini, etc.) for response generation

### Optional Integrations
- **Langfuse** - Tracing and observability platform for workflow monitoring
- **Serper API** - Google search integration for real-time information retrieval

### Environment Variables

```bash
# Required
LLM_DATABASE_POSTGRES_HOST=     # PostgreSQL host for vector storage
LLM_DATABASE_POSTGRES_PASSWORD= # Database authentication
KAFKA_BROKER_URL=               # Kafka cluster endpoint
LLM_MODEL_NAME=                 # Primary LLM model identifier
WEBHOOK_BEARER_TOKEN=           # Authentication for webhook delivery

# Optional
LANGFUSE_PUBLIC_KEY=            # Tracing and observability
SERPER_API_KEY=                 # Google search integration
DEBUG=                          # Development mode toggle
```

---

## 🔄 Common Workflows

### Chat Message Processing
1. **API Request** - FastAPI receives chat message via `/v1/chat` endpoint
2. **Kafka Queuing** - Message serialized and sent to `agent-chat` topic
3. **Worker Processing** - Background consumer executes LangGraph workflow
4. **Context Retrieval** - Vector store provides relevant conversation history
5. **Response Generation** - Multi-agent workflow generates contextual response
6. **Webhook Delivery** - Final response sent to external chat system

**Code path:** `controllers/agent.py` → `Kafka` → `workers/agent_consumer.py` → `services/agent/multi_agents.py`

### Topic Suggestion Generation
1. **Request Processing** - Analyze conversation history and room context
2. **Workflow Execution** - Dedicated suggestion workflow via LangGraph
3. **Content Analysis** - Extract themes and generate relevant topics
4. **Response Formatting** - Structure suggestions for frontend consumption

**Code path:** `controllers/agent.py` → `services/agent/multi_agents.py` → `nodes/generate_topic_suggestions.py`

---

## 📈 Performance & Scale

### Performance Considerations
- **Async Processing** - All I/O operations use async/await patterns for concurrency
- **Kafka Scaling** - Message queuing enables horizontal scaling of worker processes
- **Connection Pooling** - PostgreSQL connections managed efficiently for vector operations
- **LLM Caching** - Response caching and model selection optimization

### Monitoring
- **Metrics** - Prometheus integration for API and workflow performance tracking
- **Tracing** - Langfuse integration for LLM workflow observability
- **Logging** - Structured JSON logging with configurable levels

---

## 🚨 Things to Be Careful About

### 🔒 Security Considerations
- **API Authentication** - Webhook endpoints protected with Bearer tokens
- **Environment Variables** - Sensitive credentials managed via .env files
- **LLM Safety** - NeMo Guardrails integration for content filtering and safety

### ⚠️ Operational Concerns
- **Kafka Dependencies** - System requires Kafka availability for async processing
- **LLM Rate Limits** - External API quotas may impact response times
- **Vector Store Performance** - PostgreSQL vector operations can be resource-intensive
- **Webhook Reliability** - External system availability affects response delivery

*Updated at: 2025-01-27 UTC*