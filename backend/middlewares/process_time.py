import time
from typing import Callable

from fastapi import Request, Response


async def add_process_time_header(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    """
    FastAPI middleware that measures the time taken to process a request
    and adds an 'X-Process-Time' header to the response.

    Args:
        request: The incoming FastAPI request.
        call_next: Callable that processes the request and returns a Response.

    Returns:
        Response: The HTTP response with an added timing header.
    """
    # Record start time
    start_time = time.time()

    # Process the request
    response = await call_next(request)

    # Calculate total processing time
    process_time = time.time() - start_time

    # Attach processing time header (in seconds)
    response.headers["X-Process-Time"] = str(process_time)

    return response
