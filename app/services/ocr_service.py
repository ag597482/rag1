"""OCR service for extracting text from image-based PDFs"""
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def _check_ocr_available() -> None:
    if not OCR_AVAILABLE:
        raise ImportError(
            "OCR libraries not installed. Install with: "
            "pip install pdf2image pytesseract pillow && brew install tesseract"
        )


def extract_text_from_page_with_ocr(file_path: str, page_number: int) -> str:
    """
    Run OCR on a single PDF page (1-based). Use when pypdf extracted little/no text
    (e.g. page is a scan or image). More efficient than OCR-ing the whole file.
    """
    _check_ocr_available()
    # pdf2image uses 1-based page numbers
    images = convert_from_path(
        file_path, first_page=page_number, last_page=page_number
    )
    if not images:
        return ""
    return pytesseract.image_to_string(images[0]).strip()


def extract_text_with_ocr(file_path: str) -> str:
    """
    Extract text from image-based PDF using OCR (all pages).
    Requires: brew install tesseract (on macOS) or apt-get install tesseract-ocr (on Linux)
    """
    _check_ocr_available()
    try:
        images = convert_from_path(file_path)
        text = ""
        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            text += f"\n--- Page {i+1} ---\n{page_text}"
            print(f"✅ OCR extracted {len(page_text)} chars from page {i+1}")
        return text
    except Exception as e:
        print(f"❌ OCR extraction failed: {e}")
        raise
