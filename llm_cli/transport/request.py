"""Assemble final POST body for chat completions."""

from __future__ import annotations

from typing import Any

from llm_cli.config.models_schema import (
    Model,
    Provider,
    compat_param_mapping_resolved,
)
from llm_cli.schemas.encode import encode_schema


def build_request(
    provider: Provider,
    model: Model,
    messages: list[dict[str, Any]],
    sampling: dict[str, Any],
    extra_body: dict[str, Any],
    schema: dict[str, Any] | None = None,
    max_output_tokens: int | None = None,
) -> dict[str, Any]:
    """Build the final request body.

    Args:
        provider: Provider definition.
        model: Model definition.
        messages: Chat messages array.
        sampling: Resolved sampling params.
        extra_body: Resolved extra_body.
        schema: Optional JSON Schema.
        max_output_tokens: Resolved output token budget (from config/CLI).

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

    # Handle max_output_tokens via param_mapping
    effective_max_output = max_output_tokens
    if effective_max_output is None and "max_tokens" in sampling:
        effective_max_output = sampling["max_tokens"]

    if effective_max_output is not None:
        param_mapping = compat_param_mapping_resolved(provider)
        target_field = param_mapping.get(
            "max_output_tokens", "max_output_tokens"
        )
        # Remove any max_tokens from sampling if we're using mapped field
        if "max_tokens" in body and target_field != "max_tokens":
            body.pop("max_tokens", None)
        body[target_field] = effective_max_output

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
