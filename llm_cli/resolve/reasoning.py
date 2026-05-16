"""Reasoning level resolution and encoding."""

from __future__ import annotations


from typing import Any

from llm_cli.config.models_schema import Model

_VALID_LEVELS = {"off", "minimal", "low", "medium", "high", "xhigh"}


def encode_reasoning(
    model: Model,
    sampling: dict[str, Any],
    extra_body: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Process reasoning level from sampling and encode into request.

    Looks up sampling['reasoning'] in model.thinkingLevelMap, then encodes
    per model.thinkingFormat.

    Args:
        model: Resolved model.
        sampling: Current sampling dict (may contain 'reasoning').
        extra_body: Current extra_body dict.

    Returns:
        Tuple of (updated_sampling, updated_extra_body).

    Raises:
        SystemExit: If reasoning level is unsupported (exit code 1).
    """
    import typer

    reasoning_level = sampling.get("reasoning")
    if reasoning_level is None:
        return sampling, extra_body

    if reasoning_level == "off":
        # Remove reasoning from sampling, no encoding needed
        sampling.pop("reasoning", None)
        return sampling, extra_body

    if reasoning_level not in _VALID_LEVELS:
        typer.echo(
            f"error: reasoning level '{reasoning_level}' is not valid; "
            f"valid: {sorted(_VALID_LEVELS)}",
            err=True,
        )
        raise typer.Exit(1)

    # Check if model supports reasoning
    if not model.reasoning:
        typer.echo(
            f"error: model '{model.id}' does not support reasoning",
            err=True,
        )
        raise typer.Exit(1)

    # Look up the level in thinkingLevelMap
    level_map = model.thinking_level_map
    if level_map is None:
        typer.echo(
            f"error: model '{model.id}' has no thinkingLevelMap defined",
            err=True,
        )
        raise typer.Exit(1)

    encoded_value = level_map.get(reasoning_level)
    if encoded_value is None:
        supported = [k for k in level_map if level_map[k] is not None]
        typer.echo(
            f"error: reasoning level '{reasoning_level}' not supported by "
            f"model '{model.id}'; supported: {', '.join(sorted(supported))}",
            err=True,
        )
        raise typer.Exit(1)

    # Remove reasoning from sampling (it's been encoded elsewhere)
    sampling.pop("reasoning", None)

    # Encode per thinkingFormat
    thinking_format = model.thinking_format or "none"

    if thinking_format == "qwen-chat-template":
        chat_kwargs = extra_body.get("chat_template_kwargs", {})
        chat_kwargs["enable_thinking"] = encoded_value
        extra_body["chat_template_kwargs"] = chat_kwargs
    elif thinking_format == "openai-reasoning-effort":
        # This goes into the top-level request, not extra_body
        # We'll handle it in request.py by checking for this key
        extra_body["_reasoning_effort"] = encoded_value
    # "none" or unknown: drop the reasoning key

    return sampling, extra_body
