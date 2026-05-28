"""Pydantic models for mode definitions and sampling templates."""

from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    field_validator,
    model_validator,
)

_VALID_OUTPUT_FORMATS = {"png", "jpeg"}


class ImagePreprocessingConfig(BaseModel):
    """Configurable image preprocessing applied before sending to the model.

    All fields are Optional so layers (provider/model/mode) can override
    individual keys without restating defaults. The runtime resolver fills
    in defaults after merging.
    """

    model_config = ConfigDict(populate_by_name=True)

    enabled: bool | None = Field(
        None, description="Master switch; defaults to True when block present"
    )
    convert_rgb: bool | None = Field(
        None,
        alias="convertRgb",
        description="Convert non-RGB modes (RGBA/P/CMYK/L) to RGB",
    )
    exif_transpose: bool | None = Field(
        None,
        alias="exifTranspose",
        description="Apply EXIF orientation tag before processing",
    )
    max_long_side: int | None = Field(
        None,
        alias="maxLongSide",
        description="Downscale so the longer side is at most this many pixels",
    )
    output_format: str | None = Field(
        None,
        alias="outputFormat",
        description="Output encoding: 'png' or 'jpeg'",
    )
    jpeg_quality: int | None = Field(
        None,
        alias="jpegQuality",
        description="JPEG encoder quality (1-100); ignored for PNG output",
    )
    background: str | None = Field(
        None,
        description="Background color used to flatten alpha (e.g. 'white')",
    )

    @field_validator("max_long_side")
    @classmethod
    def _check_max_long_side(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("max_long_side must be > 0 (or null)")
        return v

    @field_validator("output_format")
    @classmethod
    def _check_output_format(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"invalid output_format '{v}'; "
                f"valid: {sorted(_VALID_OUTPUT_FORMATS)}"
            )
        return v

    @field_validator("jpeg_quality")
    @classmethod
    def _check_jpeg_quality(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 100):
            raise ValueError("jpeg_quality must be between 1 and 100")
        return v


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
    image_preprocessing: ImagePreprocessingConfig | None = Field(
        None,
        alias="imagePreprocessing",
        description="Image preprocessing overrides for this mode",
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
