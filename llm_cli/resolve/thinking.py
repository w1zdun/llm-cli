"""Thinking key routing for qwen-chat-template models."""

from __future__ import annotations

from typing import Any

from llm_cli.config.models_schema import Model


def route_thinking(
    model: Model,
    sampling: dict[str, Any],
    extra_body: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Route enable_thinking/preserve_thinking from sampling into extra_body.

    For models with `thinkingFormat = "qwen-chat-template"`, moves
    `enable_thinking` and `preserve_thinking` out of sampling and into
    `extra_body.chat_template_kwargs.*`.

    For other formats, leaves both keys untouched in sampling.

    Args:
        model: Resolved model.
        sampling: Current sampling dict (may contain thinking keys).
        extra_body: Current extra_body dict.

    Returns:
        Tuple of (updated_sampling, updated_extra_body).
    """
    thinking_format = model.thinking_format or "none"

    if thinking_format != "qwen-chat-template":
        return sampling, extra_body

    enable_thinking = sampling.pop("enable_thinking", None)
    preserve_thinking = sampling.pop("preserve_thinking", None)

    if enable_thinking is not None or preserve_thinking is not None:
        chat_kwargs = extra_body.get("chat_template_kwargs", {})
        if enable_thinking is not None:
            chat_kwargs["enable_thinking"] = enable_thinking
        if preserve_thinking is not None:
            chat_kwargs["preserve_thinking"] = preserve_thinking
        extra_body["chat_template_kwargs"] = chat_kwargs

    return sampling, extra_body
