"""Tests for layered image-preprocessing resolution."""

from __future__ import annotations

from llm_cli.config.models_schema import Model, Provider
from llm_cli.config.modes_schema import ImagePreprocessingConfig, Mode
from llm_cli.inputs.image_resolve import resolve_image_preprocessing


def _provider(**ipp_kwargs) -> Provider:
    return Provider(
        baseUrl="http://localhost/v1",
        models=[],
        imagePreprocessing=ImagePreprocessingConfig(**ipp_kwargs)
        if ipp_kwargs
        else None,
    )


def _model(**ipp_kwargs) -> Model:
    return Model(
        id="m1",
        input=["text", "image"],
        imagePreprocessing=ImagePreprocessingConfig(**ipp_kwargs)
        if ipp_kwargs
        else None,
    )


def _mode(**ipp_kwargs) -> Mode:
    return Mode(
        imagePreprocessing=ImagePreprocessingConfig(**ipp_kwargs)
        if ipp_kwargs
        else None,
    )


class TestLayerMerging:
    def test_no_layer_returns_none(self):
        result = resolve_image_preprocessing(_provider(), _model(), _mode())
        assert result is None

    def test_provider_only(self):
        result = resolve_image_preprocessing(
            _provider(maxLongSide=1024), _model(), _mode()
        )
        assert result is not None
        assert result.max_long_side == 1024
        # defaults filled
        assert result.enabled is True
        assert result.output_format == "png"

    def test_model_overrides_provider(self):
        result = resolve_image_preprocessing(
            _provider(maxLongSide=1024, outputFormat="jpeg"),
            _model(maxLongSide=2000),
            _mode(),
        )
        assert result.max_long_side == 2000
        # provider key not overridden by model carries through
        assert result.output_format == "jpeg"

    def test_mode_wins_over_model_and_provider(self):
        result = resolve_image_preprocessing(
            _provider(maxLongSide=1024),
            _model(maxLongSide=1280),
            _mode(maxLongSide=2000, jpegQuality=70),
        )
        assert result.max_long_side == 2000
        assert result.jpeg_quality == 70

    def test_mode_only(self):
        result = resolve_image_preprocessing(
            _provider(), _model(), _mode(maxLongSide=1600)
        )
        assert result is not None
        assert result.max_long_side == 1600

    def test_enabled_false_passes_through(self):
        result = resolve_image_preprocessing(
            _provider(enabled=False), _model(), _mode()
        )
        assert result is not None
        assert result.enabled is False

    def test_empty_block_uses_all_defaults(self):
        """Provider with `imagePreprocessing: {}` should opt in to defaults."""
        result = resolve_image_preprocessing(_provider(), _model(), _mode())
        # _provider() with no kwargs sets imagePreprocessing=None — so
        # empty block must be tested by passing explicit empty config.
        result = resolve_image_preprocessing(
            Provider(
                baseUrl="http://localhost/v1",
                models=[],
                imagePreprocessing=ImagePreprocessingConfig(),
            ),
            _model(),
            _mode(),
        )
        assert result is not None
        assert result.enabled is True
        assert result.max_long_side == 1280
        assert result.output_format == "png"
