"""
Stage 1 - Ingestion & Preprocessing
Converts PDFs to images, deskews, denoises, and binarizes scanned pages
so downstream OCR/layout models get the cleanest possible input.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def pdf_to_images(pdf_path: str, dpi: int = 300) -> List[Image.Image]:
    """Convert every page of a PDF into a PIL Image at the given DPI."""
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24 preferred import name
    except ImportError:
        import fitz  # older PyMuPDF versions

    images: List[Image.Image] = []
    doc = fitz.open(pdf_path)
    zoom = dpi / 72  # PDF base is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img.convert("RGB"))
    doc.close()
    return images


def load_image(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")


def deskew(image: np.ndarray) -> np.ndarray:
    """Estimate and correct page rotation using the minAreaRect of text pixels."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if coords.shape[0] < 20:
        return image  # not enough signal to safely deskew

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.1:
        return image  # already straight, avoid needless interpolation

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def denoise_and_binarize(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    binarized = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return cv2.cvtColor(binarized, cv2.COLOR_GRAY2RGB)


def preprocess_image(pil_image: Image.Image, clean: bool = False) -> Image.Image:
    """Full preprocessing pipeline: PIL in -> PIL out."""
    arr = np.array(pil_image)
    arr = deskew(arr)
    if clean:
        arr = denoise_and_binarize(arr)
    return Image.fromarray(arr)



def load_and_preprocess(path: str, dpi: int = 300) -> List[Image.Image]:
    """Entry point: accepts a PDF or image path, returns preprocessed page images."""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        pages = pdf_to_images(path, dpi=dpi)
    else:
        pages = [load_image(path)]
    return [preprocess_image(p) for p in pages]
