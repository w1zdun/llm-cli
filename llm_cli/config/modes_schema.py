"""Pydantic models for mode definitions and sampling templates."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

# Allowed sampling keys (keys that belong in sampling, not in mode/template)
_SAMPLING_KEYS = {
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "presence_penalty",
    "frequency_penalty",
    "repetition_penalty",
    "max_tokens",
    "seed",
    "stop",
    "enable_thinking",
    "preserve_thinking",
    "reasoning_effort",
    "reasoning",
    "sampling_template",
}


class Mode(BaseModel):
    """Single mode definition."""

    model_config = ConfigDict(populate_by_name=True)

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
    max_context_tokens: int | None = Field(
        None,
        alias="maxContextTokens",
        description="Client-side input token budget for this mode",
    )
    max_output_tokens: int | None = Field(
        None,
        alias="maxOutputTokens",
        description="Output token budget for this mode",
    )
    role: str | None = Field(
        None,
        description=(
            "Role of the prompt message: 'user' (default) or 'developer'. "
            "None means inherit from a lower layer."
        ),
    )

    @model_validator(mode="after")
    def _check_role(self) -> Mode:
        if self.role is not None and self.role not in ("user", "developer"):
            raise ValueError(
                f"invalid role '{self.role}'; valid: user, developer"
            )
        return self

    @property
    def effective_role(self) -> str:
        """Resolved role with 'user' as the implicit default."""
        return self.role or "user"


class SamplingTemplate(RootModel[dict[str, Any]]):
    """Sampling template — only sampling keys allowed."""

    root: dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def _reject_non_sampling(cls, data: Any) -> Any:
        if isinstance(data, dict):
            non_sampling = set(data.keys()) - _SAMPLING_KEYS
            if non_sampling:
                raise ValueError(
                    f"sampling template contains non-sampling keys: "
                    f"{', '.join(sorted(non_sampling))}. "
                    f"Only sampling keys are allowed."
                )
        return data


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
