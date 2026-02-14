"""OCR service for extracting text from image-based PDFs"""
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_with_ocr(file_path: str) -> str:
    """
    Extract text from image-based PDF using OCR.
    Requires: brew install tesseract (on macOS) or apt-get install tesseract-ocr (on Linux)
    """
    if not OCR_AVAILABLE:
        raise ImportError(
            "OCR libraries not installed. Install with: "
            "pip install pdf2image pytesseract pillow && brew install tesseract"
        )
    
    try:
        # Convert PDF pages to images
        images = convert_from_path(file_path)
        
        # Extract text from each page
        text = ""
        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            text += f"\n--- Page {i+1} ---\n{page_text}"
            print(f"✅ OCR extracted {len(page_text)} chars from page {i+1}")
        
        return text
    except Exception as e:
        print(f"❌ OCR extraction failed: {e}")
        raise
