print(f"[DEBUG] Loaded ocr_service.py from: {__file__}, module: {__name__}")
# backend/ocr_service.py
from PIL import Image, ImageOps, ImageFilter, Image
import pytesseract
import os

# If tesseract binary not in PATH, uncomment and set this path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image_pil(path):
    """Basic PIL preprocessing: convert to grayscale, increase contrast, despeckle."""
    img = Image.open(path)
    # convert to grayscale
    img = ImageOps.grayscale(img)
    # enhance
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img

def extract_text(image_path: str) -> str:
    """Extract text from image path using pytesseract. Returns raw OCR text."""
    try:
        img = preprocess_image_pil(image_path)
        text = pytesseract.image_to_string(img, lang="eng")
        return text or ""
    except Exception as e:
        # keep failures non-crashing; return message to inspect later
        return f"[OCR ERROR] {e}"
