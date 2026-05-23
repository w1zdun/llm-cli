"""Thinking key routing for qwen-chat-template models."""

from __future__ import annotations

from typing import Any

from llm_cli.config.models_schema import Model


def route_thinking(
    model: Model,
    sampling: dict[str, Any],
    extra_body: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Route enable_thinking/preserve_thinking out of sampling.

    For models with `thinkingFormat = "qwen-chat-template"`, moves
    `enable_thinking` and `preserve_thinking` out of sampling and into
    `extra_body.chat_template_kwargs.*`.

    For other formats, strips the keys from sampling — they have no
    valid wire destination and must not leak as top-level body fields.

    Args:
        model: Resolved model.
        sampling: Current sampling dict (may contain thinking keys).
        extra_body: Current extra_body dict.

    Returns:
        Tuple of (updated_sampling, updated_extra_body).
    """
    thinking_format = model.thinking_format or "none"

    enable_thinking = sampling.pop("enable_thinking", None)
    preserve_thinking = sampling.pop("preserve_thinking", None)

    if thinking_format != "qwen-chat-template":
        return sampling, extra_body

    if enable_thinking is not None or preserve_thinking is not None:
        existing = extra_body.get("chat_template_kwargs")
        chat_kwargs = dict(existing) if isinstance(existing, dict) else {}
        if enable_thinking is not None:
            chat_kwargs["enable_thinking"] = enable_thinking
        if preserve_thinking is not None:
            chat_kwargs["preserve_thinking"] = preserve_thinking
        extra_body["chat_template_kwargs"] = chat_kwargs

    return sampling, extra_body
