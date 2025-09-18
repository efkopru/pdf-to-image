# PDF to Images (PyMuPDF + Pillow)

Convert PDF pages to high-quality images (JPG, PNG, WEBP) via a simple command-line tool or an importable Python function.

---

## Features

- Per-page conversion with DPI control
- Output formats: JPG, PNG, WEBP
- Page ranges using 1-based indices
- Encrypted PDF support with passwords
- Optional grayscale conversion
- Optional downscale by max dimension
---

## Requirements

- Python 3.9+
- Packages (install with `pip install -r requirements.txt`):
  - PyMuPDF>=1.24
  - Pillow>=10.0
  - tqdm>=4.0

Some platforms may require system libraries for PyMuPDF/Pillow.

---

## Installation

```bash
# (recommended) create a virtual environment
python -m venv .venv

# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

## How to Use

# Basic: JPG at 300 DPI into a folder named after the PDF
python pdf_to_images.py input.pdf

# Custom output directory, WEBP, and quality
python pdf_to_images.py input.pdf -o out_dir --format webp --quality 90

# Convert a page range (1-based, inclusive), grayscale, and limit max dimension
python pdf_to_images.py input.pdf --start 2 --end 5 --grayscale --max-dim 2000
