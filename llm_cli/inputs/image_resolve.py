"""Resolve image-preprocessing config across provider/model/mode layers."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from llm_cli.config.models_schema import Model, Provider
from llm_cli.config.modes_schema import ImagePreprocessingConfig, Mode
from llm_cli.inputs.image_preprocess import ImagePreprocessing


def _layer_overrides(
    layer: ImagePreprocessingConfig | None,
) -> dict[str, Any]:
    """Return non-None keys from a single config layer."""
    if layer is None:
        return {}
    return {k: v for k, v in layer.model_dump().items() if v is not None}


def resolve_image_preprocessing(
    provider: Provider, model: Model, mode: Mode
) -> ImagePreprocessing | None:
    """Merge image_preprocessing across layers (provider < model < mode).

    Returns None when no layer defines preprocessing — caller should skip
    preprocessing entirely (raw bytes pass-through, backwards-compatible).
    """
    merged: dict[str, Any] = {}
    has_layer = False
    for layer in (
        provider.image_preprocessing,
        model.image_preprocessing,
        mode.image_preprocessing,
    ):
        if layer is None:
            continue
        has_layer = True
        merged.update(_layer_overrides(layer))

    if not has_layer:
        return None

    valid_keys = {f.name for f in fields(ImagePreprocessing)}
    init_kwargs = {k: v for k, v in merged.items() if k in valid_keys}
    return ImagePreprocessing(**init_kwargs)
