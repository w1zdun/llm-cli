"""Extract assistant response from provider JSON."""

from __future__ import annotations

from typing import Any


def parse_response(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """Extract content and usage from a chat completions response.

    Args:
        data: Parsed JSON response body.

    Returns:
        Tuple of (content, usage). Usage may be None.

    Raises:
        ValueError: If response shape is unexpected.
    """
    choices = data.get("choices")
    if not choices or not isinstance(choices, list) or len(choices) == 0:
        raise ValueError("unexpected response shape: no choices")

    message = choices[0].get("message")
    if not message or not isinstance(message, dict):
        raise ValueError("unexpected response shape: no message")

    content = message.get("content")
    if content is None:
        raise ValueError("unexpected response shape: content is null")

    usage = data.get("usage")
    return str(content), usage
