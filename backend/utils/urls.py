from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from utils.encoding import force_str


def replace_query_param(url: str, key: str, val: Any) -> str:
    """
    Return a new URL with the given query parameter set or replaced.

    Parses the input URL, updates the query parameter dict, and
    reconstructs the URL with the new or updated parameter.

    Args:
        url: The original URL.
        key: The query parameter name to set or replace.
        val: The value for the query parameter.

    Returns:
        The updated URL string.
    """
    # Split URL into components
    scheme, netloc, path, query, fragment = urlsplit(force_str(url))
    # Parse existing query parameters into a dict
    query_dict = parse_qs(query, keep_blank_values=True)
    # Replace or add the parameter
    query_dict[force_str(key)] = [force_str(val)]
    # Re-encode sorted parameters for consistency
    new_query = urlencode(sorted(query_dict.items()), doseq=True)
    # Reconstruct and return the full URL
    return urlunsplit((scheme, netloc, path, new_query, fragment))


def remove_query_param(url: str, key: str) -> str:
    """
    Return a new URL with the specified query parameter removed.

    Parses the input URL, removes the parameter from the query dict
    if present, and reconstructs the URL without that parameter.

    Args:
        url: The original URL.
        key: The query parameter name to remove.

    Returns:
        The updated URL string without the specified parameter.
    """
    # Split URL into components
    scheme, netloc, path, query, fragment = urlsplit(force_str(url))
    # Parse existing query parameters into a dict
    query_dict = parse_qs(query, keep_blank_values=True)
    # Remove the parameter if it exists
    query_dict.pop(force_str(key), None)
    # Re-encode sorted parameters for consistency
    new_query = urlencode(sorted(query_dict.items()), doseq=True)
    # Reconstruct and return the full URL
    return urlunsplit((scheme, netloc, path, new_query, fragment))
