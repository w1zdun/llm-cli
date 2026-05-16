"""Pydantic models for modes.json (user-defined modes)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Mode(BaseModel):
    """Single mode definition."""

    sampling: dict[str, Any] | None = Field(
        None, description="Sampling parameters for this mode"
    )
    system_prompt: str | None = Field(
        None, description="System message prepended to chat"
    )
    user_prompt_template: str | None = Field(
        None,
        alias="userPromptTemplate",
        description="Jinja2 template for user message",
    )
    output_schema: dict[str, Any] | None = Field(
        None,
        alias="schema",
        description="JSON Schema for structured output",
    )
    requires_input: str | list[str] | None = Field(
        None,
        alias="requiresInput",
        description="Required input types (text, image, pdf)",
    )
    extra_body: dict[str, Any] | None = Field(
        None, description="extra_body overrides for this mode"
    )


def parse_modes_file(raw: dict[str, Any]) -> dict[str, Mode]:
    """Parse a modes.json dict into validated Mode objects.

    Args:
        raw: Raw dict from JSONC parsing.

    Returns:
        Dict mapping mode names to validated Mode objects.
    """
    modes: dict[str, Mode] = {}
    for name, data in raw.items():
        if isinstance(data, dict):
            modes[name] = Mode(**data)
    return modes
