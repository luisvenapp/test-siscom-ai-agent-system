from prometheus_client import Counter, Histogram, Summary
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info

# Prometheus metrics definitions
DB_TOTAL = Counter(
    "dbid_requests_total",
    "Total requests by dbid.",
    ["dbid", "handler", "method", "status"],
)

TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests by handler, method, and status.",
    ["handler", "method", "status"],
)

IN_SIZE = Summary(
    "http_request_size_bytes",
    "Content length of incoming requests by handler.",
    ["handler"],
)

OUT_SIZE = Summary(
    "http_response_size_bytes",
    "Content length of outgoing responses by handler.",
    ["handler"],
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency by handler and method.",
    ["handler", "method"],
    buckets=[0.1, 0.5, 1.0],
)


def count_dbid(info: Info) -> None:
    """
    Update Prometheus metrics based on request/response data.

    Args:
        info: An Info object containing request, response, and timing data.
    """
    # Count DB-specific requests if 'dbid' exists in request.state
    if info.request and hasattr(info.request.state, "dbid"):
        DB_TOTAL.labels(
            info.request.state.dbid,
            info.modified_handler,
            info.method,
            info.modified_status,
        ).inc()

    # Count total HTTP requests
    TOTAL.labels(
        info.modified_handler,
        info.method,
        info.modified_status,
    ).inc()

    # Observe incoming request size
    content_length = int(
        info.request.headers.get("Content-Length", 0)  # type: ignore
    )
    IN_SIZE.labels(info.modified_handler).observe(content_length)

    # Observe outgoing response size if available
    if info.response and hasattr(info.response, "headers"):
        response_length = int(
            info.response.headers.get("Content-Length", 0)  # type: ignore
        )
        OUT_SIZE.labels(info.modified_handler).observe(response_length)
    else:
        OUT_SIZE.labels(info.modified_handler).observe(0)

    # Observe request latency
    LATENCY.labels(
        info.modified_handler,
        info.method,
    ).observe(info.modified_duration)


def setup_metrics(app) -> None:
    """
    Set up Prometheus instrumentation for a FastAPI application.

    Args:
        app: FastAPI application instance to instrument.
    """
    instrumentator = Instrumentator()
    instrumentator.add(count_dbid).instrument(app).expose(
        app, endpoint="/metrics"
    )
