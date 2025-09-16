import json
from functools import wraps
from json import JSONDecodeError
from typing import Any, AsyncGenerator, Generator

from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import JSONResponse, StreamingResponse

from core.logging_config import get_logger

logger = get_logger(__name__)


async def get_body(request: Request) -> Any:
    """
    Extract and cache the request body, handling JSON and multipart form data.

    On first call, parses `request.json()` or `request.form()`
    and stores the result in `request.state.body` for reuse.

    Args:
        request: Incoming HTTP request.

    Returns:
        Parsed body as dict or form data object, or empty dict on parse failure.
    """
    content_type = request.headers.get("content-type", "")
    logger.debug(f"Extracting body with content type: {content_type}")

    # Multipart form data handling
    if "multipart/form-data" in content_type:
        if not hasattr(request.state, "body"):
            request.state.body = await request.form()
            logger.debug("Form data extracted from multipart content.")

    # JSON body handling or default empty dict
    if not hasattr(request.state, "body"):
        try:
            request.state.body = await request.json()
            logger.debug("JSON body extracted successfully.")
        except JSONDecodeError:
            logger.warning(
                "Failed to decode JSON body; defaulting to empty dict."
            )
            request.state.body = {}

    return request.state.body


def serialize(func):
    """
    Decorator to serialize function return values into JSON or stream responses.

    If called with `serialize=True`, wraps:
      - AsyncGenerator -> StreamingResponse
      - Generator -> StreamingResponse with async wrapper
      - Objects with `.to_dict()` -> JSONResponse
      - Other results -> JSONResponse via `jsonable_encoder`
    Otherwise returns original result from `func`.

    Args:
        func: Async function to wrap.

    Returns:
        Wrapped async function that returns JSONResponse or StreamingResponse.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        serialize_flag = kwargs.get("serialize", False)

        # Skip serialization if not requested
        if not serialize_flag:
            return await func(*args, **kwargs)

        result = await func(*args, **kwargs)

        # Stream async generators
        if isinstance(result, AsyncGenerator):
            return StreamingResponse(content=result)

        # Stream sync generators via async adapter
        if isinstance(result, Generator):

            async def _streamer():
                for item in result:
                    yield item

            return StreamingResponse(content=_streamer())

        # Serialize objects with `to_dict` method
        try:
            if hasattr(result, "to_dict") and callable(result.to_dict):
                return JSONResponse(content=result.to_dict())
        except Exception as err:
            logger.error(f"Failed to serialize via to_dict: {err}")

        # Fallback JSON serialization
        try:
            payload = jsonable_encoder(result, exclude_none=True)
            return JSONResponse(content=payload)
        except Exception as err:
            logger.error(f"Failed to JSON-encode result: {err}")
            # Last resort: return raw JSON string
            return JSONResponse(content=json.dumps(result, default=str))

    return wrapper
