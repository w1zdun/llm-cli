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

from llm_cli.config.modes_schema import ImagePreprocessingConfig, Mode

_VALID_INPUTS = {"text", "image"}
_VALID_KINDS = {"llama.cpp", "vllm", "ollama", "openai-generic"}

# Per-kind default param_mapping for max_output_tokens
_DEFAULT_PARAM_MAPPING: dict[str, dict[str, str]] = {
    "llama.cpp": {"max_output_tokens": "max_tokens"},
    "vllm": {"max_output_tokens": "max_tokens"},
    "ollama": {"max_output_tokens": "num_predict"},
    "openai-generic": {"max_output_tokens": "max_completion_tokens"},
}

# Per-kind default file_passing
_DEFAULT_FILE_PASSING: dict[str, str] = {
    "llama.cpp": "path",
    "vllm": "path",
    "ollama": "path",
    "openai-generic": "inline",
}


def compat_param_mapping_resolved(provider: Provider) -> dict[str, str]:
    """Return merged param_mapping: per-kind defaults + user override."""
    kind = provider.provider_kind
    defaults = _DEFAULT_PARAM_MAPPING.get(kind, {})
    if provider.compat and provider.compat.param_mapping:
        merged = {**defaults, **provider.compat.param_mapping}
    else:
        merged = dict(defaults)
    return merged


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
    reasoning: bool = Field(
        False, description="Whether the model supports reasoning"
    )
    thinking_format: str | None = Field(
        None,
        alias="thinkingFormat",
        description="Reasoning encoding format",
    )
    supports_developer_role: bool = Field(
        False,
        alias="supportsDeveloperRole",
        description="Whether the model supports the developer role",
    )
    max_context_tokens: int | None = Field(
        None,
        alias="maxContextTokens",
        description="Client-side input token budget (never sent to provider)",
    )
    max_output_tokens: int | None = Field(
        None,
        alias="maxOutputTokens",
        description="Resolved output token budget (sent via param_mapping)",
    )
    modes: dict[str, Mode] | None = Field(
        None, description="Per-model mode definitions"
    )
    sampling: dict[str, Any] | None = Field(
        None, description="Per-model sampling overrides"
    )
    extra_body: dict[str, Any] | None = Field(
        None, description="Per-model extra_body overrides"
    )
    image_preprocessing: ImagePreprocessingConfig | None = Field(
        None,
        alias="imagePreprocessing",
        description="Per-model image preprocessing overrides",
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

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_fields(cls, data: Any) -> Any:
        """Reject removed legacy fields with a clear migration message."""
        if isinstance(data, dict):
            if "thinkingLevelMap" in data or "thinking_level_map" in data:
                raise ValueError(
                    "thinkingLevelMap is no longer supported. "
                    "Use enable_thinking and preserve_thinking as plain "
                    "sampling keys instead."
                )
            if "max_tokens" in data:
                raise ValueError(
                    "model.max_tokens is no longer supported. "
                    "Use maxOutputTokens (or max_output_tokens) instead."
                )
        return data


class Compat(BaseModel):
    """Provider compatibility settings."""

    model_config = ConfigDict(populate_by_name=True)

    param_mapping: dict[str, str] | None = Field(
        None,
        alias="paramMapping",
        description="Maps abstract param names to provider wire-format field names",
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
    file_passing: str | None = Field(
        None,
        alias="filePassing",
        description="How to pass files: 'path' (file:// URLs) or 'inline' (base64)",
    )
    max_context_tokens: int | None = Field(
        None,
        alias="maxContextTokens",
        description="Client-side input token budget (never sent to provider)",
    )
    max_output_tokens: int | None = Field(
        None,
        alias="maxOutputTokens",
        description="Resolved output token budget (sent via param_mapping)",
    )
    modes: dict[str, Mode] | None = Field(
        None, description="Per-provider mode definitions"
    )
    sampling: dict[str, Any] | None = Field(
        None, description="Default sampling for the provider"
    )
    extra_body: dict[str, Any] | None = Field(
        None, description="Default extra_body for the provider"
    )
    image_preprocessing: ImagePreprocessingConfig | None = Field(
        None,
        alias="imagePreprocessing",
        description="Default image preprocessing for the provider",
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

    @model_validator(mode="after")
    def _fill_file_passing_default(self) -> Provider:
        """Fill file_passing from per-kind default if not set."""
        if self.file_passing is None:
            self.file_passing = _DEFAULT_FILE_PASSING.get(
                self.provider_kind, "inline"
            )
        return self


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
    sampling_templates: dict[str, dict[str, Any]] | None = Field(
        None,
        alias="samplingTemplates",
        description="Named sampling parameter bundles",
    )
    modes: dict[str, Mode] | None = Field(
        None,
        description="Global mode definitions (apply to all providers/models)",
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
