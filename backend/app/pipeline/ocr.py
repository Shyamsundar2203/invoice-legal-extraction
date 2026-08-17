"""
Stage 3 - OCR
Wraps Tesseract (via pytesseract) to return word-level text, bounding boxes,
and confidence scores. Swap `run_ocr` internals for PaddleOCR/docTR/TrOCR
without touching any downstream code -- they all consume the same OCRWord list.
"""
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def _init_tesseract():
    """Auto-detect Tesseract executable location across OS environments."""
    if shutil.which("tesseract"):
        return
    custom_cmd = os.getenv("TESSERACT_CMD")
    if custom_cmd and Path(custom_cmd).exists():
        pytesseract.pytesseract.tesseract_cmd = custom_cmd
        return
    win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for path in win_paths:
        if Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = path
            break


_init_tesseract()



@dataclass
class OCRWord:
    text: str
    conf: float          # 0-1
    bbox: List[float]    # [x0, y0, x1, y1] pixel coords
    line_num: int
    block_num: int


def run_ocr(image: Image.Image, lang: str = "eng") -> List[OCRWord]:
    """Run Tesseract OCR and return structured word-level results."""
    data = pytesseract.image_to_data(
        image, lang=lang, output_type=pytesseract.Output.DICT
    )

    words: List[OCRWord] = []
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        conf_raw = data["conf"][i]
        try:
            conf = max(float(conf_raw), 0.0) / 100.0
        except (ValueError, TypeError):
            conf = 0.0
        x, y, w, h = (
            data["left"][i],
            data["top"][i],
            data["width"][i],
            data["height"][i],
        )
        words.append(
            OCRWord(
                text=text,
                conf=conf,
                bbox=[float(x), float(y), float(x + w), float(y + h)],
                line_num=data["line_num"][i],
                block_num=data["block_num"][i],
            )
        )
    return words


def words_to_text(words: List[OCRWord]) -> str:
    """Reconstruct reading-order text, grouped by block/line, from OCR words."""
    lines: dict = {}
    for w in words:
        key = (w.block_num, w.line_num)
        lines.setdefault(key, []).append(w.text)
    ordered_keys = sorted(lines.keys())
    return "\n".join(" ".join(lines[k]) for k in ordered_keys)


def average_confidence(words: List[OCRWord]) -> float:
    if not words:
        return 0.0
    return sum(w.conf for w in words) / len(words)
