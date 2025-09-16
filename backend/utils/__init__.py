import json
import os
import re
import secrets
import uuid
from typing import Any, Dict, List, Optional, Union

RANDOM_STRING_CHARS = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
)


def get_env(name: str, default: Any = None) -> Any:
    """
    Retrieve an environment variable or return a default value.

    Args:
        name: Name of the environment variable.
        default: Value to return if the variable is not set.

    Returns:
        The environment variable value or the default.
    """
    return os.environ.get(name, default)


def password_file(
    file_env_name: str,
    env_name: str,
    default: Any = None,
) -> Any:
    """
    Retrieve a password from a file or an environment variable.

    Args:
        file_env_name: Env var name containing the path to a password file.
        env_name: Env var name for the password itself.
        default: Default value if neither is set.

    Returns:
        The password string or the default.
    """
    file_path = os.environ.get(file_env_name)
    if file_path and os.path.isfile(file_path) and os.access(file_path, os.R_OK):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return get_env(env_name, default)


def bool_from_str(value: Optional[str]) -> Optional[bool]:
    """
    Convert a string to a boolean.

    Args:
        value: Input string representation of a boolean.

    Returns:
        True, False, or None if conversion is not possible.
    """
    if value is None:
        return None
    val = value.lower()
    if val in ("true", "1", "yes", "y", "t"):
        return True
    if val in ("false", "0", "no", "n", "f"):
        return False
    return None


def get_random_string(length: int, allowed_chars: str = RANDOM_STRING_CHARS) -> str:
    """
    Generate a securely random string of the given length.

    Args:
        length: Length of the random string.
        allowed_chars: Characters to choose from.

    Returns:
        A securely generated random string.
    """
    return "".join(secrets.choice(allowed_chars) for _ in range(length))


def validate_url(value: Optional[str]) -> Optional[str]:
    """
    Validate and normalize a URL string.

    Args:
        value: URL to validate.

    Returns:
        The normalized URL without a trailing slash, or None if input is None.

    Raises:
        ValueError: If the URL is invalid.
    """
    if value is None:
        return None

    pattern = (
        r"^(?:http)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
        r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|localhost|web|"
        r"\d{1,3}(?:\.\d{1,3}){3})"  # domain or IPv4
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$"
    )
    regex = re.compile(pattern, re.IGNORECASE)
    if regex.match(value):
        return value.rstrip("/")
    raise ValueError(
        f"Invalid URL: {value}. "
        "Examples: http://example.com, https://example.com"
    )


def path_join(*paths: str) -> str:
    """
    Join multiple paths into a single filesystem path.

    Args:
        *paths: Path segments to join.

    Returns:
        The combined file path.
    """
    return os.path.join(*paths)


def to_dict(data: Any) -> Dict[str, Any]:
    """
    Convert an object to a dict via JSON serialization.

    Args:
        data: Serializable object.

    Returns:
        A dict representation of the object.
    """
    json_str = json.dumps(data, default=str).replace("\\u0000", "")
    return json.loads(json_str)


def positive_int(
    integer_string: Union[str, int],
    strict: bool = False,
    cutoff: Optional[int] = None,
) -> int:
    """
    Convert a value to a strictly positive integer.

    Args:
        integer_string: Value to convert.
        strict: If True, zero is not allowed.
        cutoff: Maximum allowed value.

    Returns:
        A positive integer, possibly capped by cutoff.

    Raises:
        ValueError: If conversion fails or strict conditions are not met.
    """
    value = int(integer_string)
    if value < 0 or (strict and value == 0):
        raise ValueError("Value must be positive")
    if cutoff is not None:
        return min(value, cutoff)
    return value


def get_random_filename(filename: str) -> str:
    """
    Generate a random filename preserving the original extension.

    Args:
        filename: Original filename.

    Returns:
        A new filename with a UUID and the original extension.
    """
    ext = os.path.splitext(filename)[1].lstrip(".")
    return f"{uuid.uuid4()}.{ext}"


def format_error_response(
    status: int,
    error_type: str,
    field: str,
    message: str,
    details: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Format a standardized error response payload.

    Args:
        status: HTTP status code.
        error_type: Type of error.
        field: Field name associated with the error.
        message: Descriptive error message.
        details: Optional list of detailed error info.

    Returns:
        A dict suitable for a JSON error response.
    """
    return {
        "status": status,
        "error": {
            "type": error_type,
            "field": field,
            "message": message,
            "details": details,
        },
    }
