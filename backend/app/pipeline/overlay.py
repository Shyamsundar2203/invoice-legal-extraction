"""
Stage 6 - Visual overlay generation.
Draws confidence-color-coded bounding boxes for extracted fields on top of
the original page image and saves the result as a PDF for human review.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from app.pipeline.ocr import OCRWord

HIGH_CONF_COLOR = (34, 139, 34)     # green
MED_CONF_COLOR = (255, 165, 0)      # orange
LOW_CONF_COLOR = (220, 20, 60)      # red


def _color_for_confidence(conf: float):
    if conf >= 0.85:
        return HIGH_CONF_COLOR
    if conf >= 0.6:
        return MED_CONF_COLOR
    return LOW_CONF_COLOR


def draw_overlay(image: Image.Image, words: List[OCRWord]) -> Image.Image:
    """Draw a bounding box + confidence color for every OCR word."""
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    for w in words:
        color = _color_for_confidence(w.conf)
        draw.rectangle(w.bbox, outline=color, width=2)
    return overlay


def save_overlay_pdf(images: List[Image.Image], output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if not images:
        raise ValueError("No images provided for overlay PDF")
    first, rest = images[0], images[1:]
    first.save(output_path, save_all=True, append_images=rest)
    return output_path
