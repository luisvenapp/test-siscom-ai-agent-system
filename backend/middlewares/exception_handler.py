import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from exceptions import ImproperlyConfigured, RequestValidationError
from utils import format_error_response
from core.logging_config import get_logger

logger = get_logger("ExceptionHandler")


def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for FastAPI.

    Logs the exception with traceback and returns a JSON response
    tailored to the exception type.

    Args:
        request: The incoming FastAPI request.
        exc: The exception instance.

    Returns:
        JSONResponse: Structured error response.
    """
    # Attempt to log the error and full traceback
    try:
        tb = traceback.format_exc()
        logger.error(
            f"Error in {request.method} {request.url.path} - {exc}",
            extra={"traceback": tb},
        )
    except Exception as log_exc:
        # Fallback logging failure
        logger.error(
            f"Error in exception_handler logging: {log_exc}"
        )

    # Handle custom RequestValidationError
    if isinstance(exc, RequestValidationError):
        try:
            first_err = exc.errors()[0]
            field = first_err.get("loc", ["unknown"])[-1]
            message = first_err.get("msg", "Validation error")
        except Exception:
            # Default if .errors() is not as expected
            field = "unknown"
            message = str(exc)
        return JSONResponse(
            status_code=422,
            content=format_error_response(
                status=422,
                error_type="CustomValidationError",
                field=field,
                message=message,
            ),
        )

    # Handle Pydantic ValidationError
    if isinstance(exc, ValidationError):
        formatted_errors = []
        for err in exc.errors():
            loc = err.get("loc", ["unknown"])
            field = loc[-1] if loc else "unknown"
            formatted_errors.append(
                {
                    "field": field,
                    "message": err.get("msg", "No message provided"),
                    "type": err.get("type", "unknown_type"),
                }
            )
        return JSONResponse(
            status_code=422,
            content=format_error_response(
                status=422,
                error_type="ValidationError",
                field="multiple_fields",
                message="Validation error in the request body.",
                details=formatted_errors,
            ),
        )

    # Handle configuration errors
    if isinstance(exc, ImproperlyConfigured):
        return JSONResponse(
            status_code=500,
            content=format_error_response(
                status=500,
                error_type="ImproperlyConfigured",
                field="settings",
                message=getattr(exc, "message", "Configuration error"),
            ),
        )

    # Default response for unhandled exceptions
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_server_error",
            "detail": "Internal Server Error",
        },
    )
