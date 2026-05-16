"""Validate assistant output against JSON Schema."""

from __future__ import annotations

from typing import Any

import jsonschema


def validate_output(
    content: str,
    schema: dict[str, Any],
) -> Any:
    """Parse and validate assistant content against a JSON Schema.

    Args:
        content: Raw assistant content string.
        schema: JSON Schema dict.

    Returns:
        Validated Python object.

    Raises:
        jsonschema.ValidationError: If validation fails.
        ValueError: If content is not valid JSON.
    """
    import json

    # Parse JSON
    try:
        obj = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"response is not valid JSON: {exc}") from exc

    # Validate against schema
    jsonschema.validate(instance=obj, schema=schema)
    return obj
