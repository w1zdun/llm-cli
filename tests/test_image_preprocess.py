"""Tests for image preprocessing pipeline."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from llm_cli.inputs.image_preprocess import (
    ImagePreprocessing,
    preprocess_image_bytes,
)


def _encode(img: Image.Image, fmt: str = "PNG", **kwargs) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()


def _decode(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


class TestRgbConvert:
    def test_rgba_flattens_alpha_on_white(self):
        rgba = Image.new("RGBA", (16, 16), (255, 0, 0, 0))  # transparent red
        cfg = ImagePreprocessing()
        data, mime = preprocess_image_bytes(_encode(rgba), "image/png", cfg)

        out = _decode(data)
        assert out.mode == "RGB"
        # Fully transparent → background (white) shows through
        assert out.getpixel((0, 0)) == (255, 255, 255)
        assert mime == "image/png"

    def test_palette_with_transparency_converts_to_rgb(self):
        p = Image.new("P", (16, 16))
        p.info["transparency"] = 0
        cfg = ImagePreprocessing()
        data, _ = preprocess_image_bytes(_encode(p), "image/png", cfg)
        out = _decode(data)
        assert out.mode == "RGB"

    def test_grayscale_to_rgb(self):
        gray = Image.new("L", (16, 16), 128)
        cfg = ImagePreprocessing()
        data, _ = preprocess_image_bytes(_encode(gray), "image/png", cfg)
        out = _decode(data)
        assert out.mode == "RGB"

    def test_convert_rgb_disabled_preserves_mode(self):
        rgba = Image.new("RGBA", (16, 16), (255, 0, 0, 128))
        cfg = ImagePreprocessing(convert_rgb=False, output_format="png")
        data, _ = preprocess_image_bytes(_encode(rgba), "image/png", cfg)
        out = _decode(data)
        assert out.mode == "RGBA"


class TestExifTranspose:
    def test_orientation_6_rotates_dimensions(self):
        # orientation=6 means the camera was rotated 90° CW → display rotates back
        img = Image.new("RGB", (100, 50), "red")
        buf = io.BytesIO()
        # Pillow can write EXIF orientation
        exif = img.getexif()
        exif[0x0112] = 6  # Orientation tag
        img.save(buf, format="JPEG", exif=exif)

        cfg = ImagePreprocessing(exif_transpose=True)
        data, _ = preprocess_image_bytes(buf.getvalue(), "image/jpeg", cfg)
        out = _decode(data)
        # Rotation swaps width/height
        assert out.size == (50, 100)

    def test_orientation_disabled_keeps_dimensions(self):
        img = Image.new("RGB", (100, 50), "red")
        buf = io.BytesIO()
        exif = img.getexif()
        exif[0x0112] = 6
        img.save(buf, format="JPEG", exif=exif)

        cfg = ImagePreprocessing(exif_transpose=False)
        data, _ = preprocess_image_bytes(buf.getvalue(), "image/jpeg", cfg)
        out = _decode(data)
        assert out.size == (100, 50)


class TestScaling:
    def test_downscale_landscape(self):
        img = Image.new("RGB", (4000, 3000), "red")
        cfg = ImagePreprocessing(max_long_side=1280)
        data, _ = preprocess_image_bytes(_encode(img), "image/png", cfg)
        out = _decode(data)
        assert out.size == (1280, 960)

    def test_downscale_portrait(self):
        img = Image.new("RGB", (3000, 4000), "red")
        cfg = ImagePreprocessing(max_long_side=1280)
        data, _ = preprocess_image_bytes(_encode(img), "image/png", cfg)
        out = _decode(data)
        assert out.size == (960, 1280)

    def test_no_upscale(self):
        img = Image.new("RGB", (800, 600), "red")
        cfg = ImagePreprocessing(max_long_side=1280)
        data, _ = preprocess_image_bytes(_encode(img), "image/png", cfg)
        out = _decode(data)
        assert out.size == (800, 600)

    def test_max_long_side_none_skips_scaling(self):
        img = Image.new("RGB", (4000, 3000), "red")
        cfg = ImagePreprocessing(max_long_side=None)
        data, _ = preprocess_image_bytes(_encode(img), "image/png", cfg)
        out = _decode(data)
        assert out.size == (4000, 3000)


class TestOutputFormat:
    def test_png_output_mime(self):
        img = Image.new("RGB", (16, 16), "red")
        cfg = ImagePreprocessing(output_format="png")
        data, mime = preprocess_image_bytes(_encode(img), "image/png", cfg)
        assert mime == "image/png"
        out = _decode(data)
        assert out.format == "PNG"

    def test_jpeg_output_mime(self):
        img = Image.new("RGB", (16, 16), "red")
        cfg = ImagePreprocessing(output_format="jpeg", jpeg_quality=80)
        data, mime = preprocess_image_bytes(_encode(img), "image/png", cfg)
        assert mime == "image/jpeg"
        out = _decode(data)
        assert out.format == "JPEG"

    def test_jpeg_re_encodes_rgba_source(self):
        rgba = Image.new("RGBA", (16, 16), (255, 0, 0, 200))
        cfg = ImagePreprocessing(output_format="jpeg")
        data, mime = preprocess_image_bytes(_encode(rgba), "image/png", cfg)
        assert mime == "image/jpeg"
        out = _decode(data)
        assert out.mode == "RGB"


class TestBackgroundFlatten:
    def test_custom_background_color(self):
        rgba = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        cfg = ImagePreprocessing(background="black")
        data, _ = preprocess_image_bytes(_encode(rgba), "image/png", cfg)
        out = _decode(data)
        assert out.getpixel((0, 0)) == (0, 0, 0)


class TestRealisticScenarios:
    def test_4k_screenshot_shrinks(self):
        """A 4K UI screenshot should fit into ~1280px and lose bytes."""
        img = Image.new("RGB", (3840, 2160), "red")
        raw = _encode(img)
        cfg = ImagePreprocessing(max_long_side=1280, output_format="png")
        data, _ = preprocess_image_bytes(raw, "image/png", cfg)
        out = _decode(data)
        assert out.size == (1280, 720)
        # Solid colour PNG is tiny either way, but processed must not exceed raw
        assert len(data) <= len(raw)


@pytest.fixture(autouse=True)
def _no_pillow_decompression_bomb_warnings():
    # The synthetic images stay well under Pillow's bomb threshold.
    yield
