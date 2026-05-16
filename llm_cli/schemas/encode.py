"""Encode schema into request body per provider_kind."""

from __future__ import annotations

import sys
from typing import Any

from llm_cli.config.models_schema import Provider


def _response_format(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "schema",
                "schema": schema,
                "strict": True,
            },
        }
    }


def encode_schema(
    schema: dict[str, Any],
    provider: Provider,
) -> dict[str, Any]:
    """Encode schema into request fields per provider_kind."""
    kind = provider.provider_kind

    if kind == "llama.cpp":
        return _response_format(schema)

    if kind == "vllm":
        return {"extra_body": {"guided_json": schema}}

    if kind == "ollama":
        return {"format": schema}

    print(
        f"warning: provider '{kind}' using fallback response_format encoding",
        file=sys.stderr,
    )
    return _response_format(schema)
