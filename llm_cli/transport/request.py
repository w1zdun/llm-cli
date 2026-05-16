"""Assemble final POST body for chat completions."""

from __future__ import annotations

from typing import Any

from llm_cli.config.models_schema import Model, Provider
from llm_cli.schemas.encode import encode_schema


def build_request(
    provider: Provider,
    model: Model,
    messages: list[dict[str, Any]],
    sampling: dict[str, Any],
    extra_body: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the final request body.

    Args:
        provider: Provider definition.
        model: Model definition.
        messages: Chat messages array.
        sampling: Resolved sampling params.
        extra_body: Resolved extra_body.
        schema: Optional JSON Schema.

    Returns:
        Complete request body dict.
    """
    body: dict[str, Any] = {
        "model": model.id,
        "messages": messages,
        "stream": False,
    }

    # Add sampling params (flattened into top-level)
    for key, value in sampling.items():
        body[key] = value

    # Handle max_tokens field name per provider compat
    if "max_tokens" in sampling:
        max_tokens_field = "max_tokens"
        if provider.compat and provider.compat.max_tokens_field:
            max_tokens_field = provider.compat.max_tokens_field
        if max_tokens_field != "max_tokens":
            body[max_tokens_field] = body.pop("max_tokens")

    # Handle reasoning_effort (from qwen-chat-template encoding)
    reasoning_effort = extra_body.pop("_reasoning_effort", None)
    if reasoning_effort is not None:
        body["reasoning_effort"] = reasoning_effort

    # Flatten extra_body into top-level
    if extra_body:
        for key, value in extra_body.items():
            body[key] = value

    # Encode schema if present
    if schema:
        schema_fields = encode_schema(schema, provider)
        # Handle extra_body from schema encoding (vllm)
        schema_extra = schema_fields.pop("extra_body", None)
        if schema_extra:
            for key, value in schema_extra.items():
                body[key] = value
        body.update(schema_fields)

    return body
