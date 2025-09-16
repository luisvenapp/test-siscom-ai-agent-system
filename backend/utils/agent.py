import re
from typing import Any, Dict, List

import tiktoken
from core.logging_config import get_logger
from langchain_core.runnables.graph import MermaidDrawMethod

logger = get_logger(__name__)


def export_to_mermaid(workflow: Any, name: str) -> None:
    """
    Render a workflow graph as a Mermaid PNG and save to file.

    Args:
        workflow: An object with a `get_graph()` method that returns
            an object supporting `draw_mermaid_png`.
        name: Filename (without extension) to save the PNG.
    """
    # Draw the graph via Mermaid API
    png_bytes = workflow.get_graph().draw_mermaid_png(
        draw_method=MermaidDrawMethod.API
    )

    # Write the PNG bytes to disk
    with open(f"{name}.png", "wb") as file:
        file.write(png_bytes)


def num_tokens_from_messages(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-2024-08-06",
) -> int:
    """
    Calculate the approximate number of tokens used by a list of messages.

    Uses tiktoken to encode message values and accounts for model-specific
    token offsets per message and per name field.

    Args:
        messages: List of dicts representing chat messages.
        model: Model identifier to select encoding rules.

    Returns:
        Total token count for the provided messages.

    Raises:
        NotImplementedError: If token counting is not supported for the model.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning("Model not found; using 'o200k_base' encoding.")
        encoding = tiktoken.get_encoding("o200k_base")

    # Determine token costs for known models
    if model in {
        "gpt-3.5-turbo-0125",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-2024-08-06",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif "gpt-3.5-turbo" in model:
        logger.warning(
            "gpt-3.5-turbo may update; "
            "assuming 'gpt-3.5-turbo-0125'."
        )
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0125")
    elif "gpt-4o-mini" in model:
        logger.warning(
            "gpt-4o-mini may update; "
            "assuming 'gpt-4o-mini-2024-07-18'."
        )
        return num_tokens_from_messages(
            messages, model="gpt-4o-mini-2024-07-18"
        )
    elif "gpt-4o" in model:
        logger.warning(
            "gpt-4o may update; assuming 'gpt-4o-2024-08-06'."
        )
        return num_tokens_from_messages(messages, model="gpt-4o-2024-08-06")
    elif "gpt-4" in model:
        logger.warning(
            "gpt-4 may update; assuming 'gpt-4-0613'."
        )
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"num_tokens_from_messages not implemented for model {model}"
        )

    # Count tokens for each message
    total_tokens = 0
    for message in messages:
        total_tokens += tokens_per_message
        for key, value in message.items():
            total_tokens += len(encoding.encode(value))
            if key == "name":
                total_tokens += tokens_per_name

    # Account for priming tokens in assistant response
    total_tokens += 3
    return total_tokens


def remove_think_content(response_text: str) -> str:
    """
    Strip out <think>…</think> blocks from LLM response text.

    If a stray </think> remains without a matching <think>, remove
    all text up to and including that closing tag.

    Args:
        response_text: Raw LLM response containing potential think tags.

    Returns:
        Cleaned text without think content.
    """
    # Remove well-formed think blocks
    cleaned = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL)
    # Remove any leading stray closing tag
    cleaned = re.sub(r"^.*?</think>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()
