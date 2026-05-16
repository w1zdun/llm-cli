"""Pydantic models for models.json (providers + models registry)."""

from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

_VALID_INPUTS = {"text", "image"}
_VALID_KINDS = {"llama.cpp", "vllm", "ollama", "openai-generic"}


class Model(BaseModel):
    """Single model entry under a provider."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Model id sent in the request")
    name: str | None = Field(None, description="Display name")
    input: list[str] = Field(
        default=["text"], description="Supported input modalities"
    )
    context_window: int | None = Field(
        None, alias="contextWindow", description="Context window size in tokens"
    )
    max_tokens: int | None = Field(None, description="Max output tokens")
    reasoning: bool = Field(
        False, description="Whether the model supports reasoning"
    )
    thinking_format: str | None = Field(
        None,
        alias="thinkingFormat",
        description="Reasoning encoding format",
    )
    thinking_level_map: dict[str, Any] | None = Field(
        None,
        alias="thinkingLevelMap",
        description="Maps abstract reasoning levels to model-specific values",
    )
    sampling: dict[str, Any] | None = Field(
        None, description="Per-model sampling overrides"
    )
    extra_body: dict[str, Any] | None = Field(
        None, description="Per-model extra_body overrides"
    )

    @field_validator("input")
    @classmethod
    def _check_inputs(cls, v: list[str]) -> list[str]:
        for item in v:
            if item not in _VALID_INPUTS:
                raise ValueError(
                    f"invalid input modality '{item}'; valid: {sorted(_VALID_INPUTS)}"
                )
        return v


class Compat(BaseModel):
    """Provider compatibility settings."""

    model_config = ConfigDict(populate_by_name=True)

    max_tokens_field: str | None = Field(
        None,
        alias="maxTokensField",
        description="Field name for max tokens (e.g. max_completion_tokens)",
    )


class Provider(BaseModel):
    """Provider definition in models.json."""

    model_config = ConfigDict(populate_by_name=True)

    base_url: str = Field(
        alias="baseUrl", description="Base URL for the provider API"
    )
    api: str = Field(
        "openai-completions", description="API type (reserved for future)"
    )
    provider_kind: str = Field(
        "openai-generic",
        alias="providerKind",
        description="Provider kind for schema encoding",
    )
    api_key: str | None = Field(
        None, alias="apiKey", description="Bearer token for authentication"
    )
    compat: Compat | None = Field(None, description="Compatibility settings")
    sampling: dict[str, Any] | None = Field(
        None, description="Default sampling for the provider"
    )
    extra_body: dict[str, Any] | None = Field(
        None, description="Default extra_body for the provider"
    )
    models: list[Model] = Field(description="List of models for this provider")

    @field_validator("provider_kind")
    @classmethod
    def _check_kind(cls, v: str) -> str:
        if v not in _VALID_KINDS:
            raise ValueError(
                f"unknown provider_kind '{v}'; valid: {sorted(_VALID_KINDS)}"
            )
        return v


class ProvidersFile(BaseModel):
    """Top-level models.json structure."""

    model_config = ConfigDict(populate_by_name=True)

    providers: dict[str, Provider] = Field(description="Named providers")
    default_provider: str | None = Field(
        None,
        alias="defaultProvider",
        description="Default provider name",
    )
    default_model: str | None = Field(
        None,
        alias="defaultModel",
        description="Default model id (scoped to provider)",
    )

    @model_validator(mode="after")
    def _check_default_provider(self) -> ProvidersFile:
        if (
            self.default_provider
            and self.default_provider not in self.providers
        ):
            raise ValueError(
                f"default_provider '{self.default_provider}' not in providers"
            )
        return self
