import re
from typing import Any, Dict, List

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle FastAPI request validation errors and format them into a
    structured JSON response.

    Args:
        request: The incoming HTTP request.
        exc: The RequestValidationError exception instance.

    Returns:
        JSONResponse containing a list of formatted error details.
    """
    formatted_errors: List[Dict[str, Any]] = []

    # Iterate through each Pydantic validation error
    for err in exc.errors():
        error_type = err.get("type")
        location_parts = err.get("loc", [])
        # Join the error location into a readable string
        location = " -> ".join(str(part) for part in location_parts)

        # Extract the primary error message (first line)
        raw_msg = err.get("msg", "")
        main_message = raw_msg.split("\n", 1)[0]

        # Find tool-specific sub-errors within the multiline message
        tool_errors: List[Dict[str, str]] = []
        pattern = r"(actual_instance\..*?type\n\s*Value error,.*)"
        matches = re.findall(pattern, raw_msg, flags=re.DOTALL)

        # Parse each matched sub-error block
        for match in matches:
            lines = match.splitlines()
            if len(lines) >= 2:
                tool_errors.append({
                    "location": lines[0].strip(),
                    "message": lines[1].strip(),
                    "help_url": (
                        "https://errors.pydantic.dev/2.8/v/value_error"
                    ),
                })

        formatted_errors.append({
            "location": location,
            "message": main_message,
            "type": error_type,
            "tool_errors": tool_errors,
        })

    # Return a unified JSON response with all formatted errors
    return JSONResponse(status_code=422, content={"detail": formatted_errors})
