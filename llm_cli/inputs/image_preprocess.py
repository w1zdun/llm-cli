"""Image preprocessing pipeline: EXIF, RGB, scaling, re-encode."""

from __future__ import annotations

import io
from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePreprocessing:
    """Resolved preprocessing settings used by the inputs pipeline."""

    enabled: bool = True
    convert_rgb: bool = True
    exif_transpose: bool = True
    max_long_side: int | None = 1280
    output_format: str = "png"
    jpeg_quality: int = 90
    background: str = "white"


_FORMAT_TO_MIME = {"png": "image/png", "jpeg": "image/jpeg"}


def preprocess_image_bytes(
    data: bytes, source_mime: str, cfg: ImagePreprocessing
) -> tuple[bytes, str]:
    """Apply preprocessing and return (new_bytes, new_mime).

    Pipeline (each step is a config flag):
      1. EXIF transpose — rotate to display orientation
      2. RGB convert — flatten alpha onto solid background, drop palette/CMYK
      3. Resize (LANCZOS) — only downscale, never upscale
      4. Re-encode to PNG or JPEG
    """
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(data))
    img.load()

    if cfg.exif_transpose:
        img = ImageOps.exif_transpose(img)

    if cfg.convert_rgb and img.mode != "RGB":
        if img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        ):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, cfg.background)
            bg.paste(rgba, mask=rgba.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

    if cfg.max_long_side is not None:
        w, h = img.size
        longest = max(w, h)
        if longest > cfg.max_long_side:
            scale = cfg.max_long_side / longest
            new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
            img = img.resize(new_size, Image.LANCZOS)

    out = io.BytesIO()
    fmt = cfg.output_format
    if fmt == "jpeg":
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(out, format="JPEG", quality=cfg.jpeg_quality, optimize=True)
    else:
        img.save(out, format="PNG", optimize=True)

    return out.getvalue(), _FORMAT_TO_MIME[fmt]
