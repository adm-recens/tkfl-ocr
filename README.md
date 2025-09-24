# Voucher OCR Prototype (Flask + SQLite + Tesseract)

## Purpose
Simple prototype: upload receipt images, run OCR locally (pytesseract), parse into a JSON structure, and store into a SQLite master table for later analytics.

## Prerequisites
- Python 3.8+
- Tesseract OCR binary installed and available in PATH:
  - Windows: install from UB-Mannheim build and add `C:\Program Files\Tesseract-OCR` to PATH.
  - macOS: `brew install tesseract`
  - Linux: `sudo apt install tesseract-ocr`

## Setup (Windows / PowerShell)
```powershell
# from project root (tkfl-ocr)
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
