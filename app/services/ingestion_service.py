import re
from typing import List, Dict, Tuple
from pypdf import PdfReader
from openai import OpenAI
from app.core.config import settings
from app.db.vector_store import VectorStore
from app.db.metadata_store import MetadataStore

client = OpenAI(api_key=settings.OPENAI_API_KEY)
vector_store = VectorStore()
metadata_store = MetadataStore()

# Division keywords that PDFs commonly use for structuring content.
# Order matters: more specific/longer keywords first to avoid partial matches.
DIVISION_KEYWORDS = [
    "chapter", "unit", "part", "section", "lesson",
    "lecture", "module", "topic", "week", "session",
    "volume", "book", "act", "episode", "phase",
    "segment", "block", "lab", "tutorial", "exercise",
    "assignment", "appendix", "supplement",
]

# Number words for matching "Chapter One", "Lecture Two", etc.
NUMBER_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|"
    "eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    "eighteen|nineteen|twenty|thirty|forty|fifty"
)

def _build_chapter_patterns():
    """Build flexible regex patterns for all division keywords.
    
    Each keyword generates patterns matching things like:
      Lecture 1, Lecture #1, Lecture-1, Lecture: 1,
      LECTURE ONE, lecture #12: Introduction, etc.
    """
    patterns = []
    for kw in DIVISION_KEYWORDS:
        # "Keyword <number>" — e.g. Chapter 1, Lecture 12
        patterns.append(rf"(?im)^{kw}\s*[#:\-–—]?\s*\d+")
        # "Keyword <word-number>" — e.g. Chapter One, Unit Two
        patterns.append(rf"(?im)^{kw}\s*[#:\-–—]?\s*({NUMBER_WORDS})")
    return patterns

CHAPTER_PATTERNS = _build_chapter_patterns()


def extract_pages(file_path: str) -> List[Dict]:
    """Extract text from PDF page by page.
    
    Returns a list of dicts: [{page_number: int, text: str}, ...]
    """
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        
        # If very little text, try OCR for this page
        if len(text.strip()) < 20:
            try:
                from app.services.ocr_service import extract_text_with_ocr
                # OCR the whole file and get the page text
                # For efficiency, we only do OCR if the whole PDF seems image-based
                pass  # OCR fallback handled at PDF level below
            except ImportError:
                pass
        
        pages.append({
            "page_number": i + 1,
            "text": text,
        })
    
    # If total extracted text is very small, try OCR for the whole file
    total_text = "".join(p["text"] for p in pages)
    if len(total_text.strip()) < 100:
        print("⚠️ Little text extracted with pypdf, attempting OCR...")
        try:
            from app.services.ocr_service import extract_text_with_ocr
            ocr_text = extract_text_with_ocr(file_path)
            # Re-split by page markers from OCR output
            ocr_pages = ocr_text.split("\n--- Page ")
            for j, ocr_page in enumerate(ocr_pages):
                if j == 0 and not ocr_page.strip():
                    continue
                page_idx = j - 1 if j > 0 else 0
                if page_idx < len(pages):
                    # Remove "X ---\n" prefix from OCR page
                    clean_text = re.sub(r"^\d+\s*---\n?", "", ocr_page)
                    pages[page_idx]["text"] = clean_text
        except (ImportError, Exception) as e:
            print(f"⚠️ OCR not available or failed: {e}")
    
    return pages


def detect_chapters(pages: List[Dict]) -> Dict[str, List[int]]:
    """Detect chapter/unit boundaries from page texts.
    
    Returns a dict mapping chapter names to list of page numbers.
    E.g. {"Chapter 1: Introduction": [1, 2, 3], "Chapter 2: Basics": [4, 5, 6]}
    """
    chapter_boundaries = []  # [(page_number, chapter_title)]
    
    for page in pages:
        text = page["text"]
        page_num = page["page_number"]
        
        for pattern in CHAPTER_PATTERNS:
            match = re.search(pattern, text)
            if match:
                # Extract the full chapter title line
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                if line_end == -1:
                    line_end = min(match.end() + 100, len(text))
                chapter_title = text[line_start:line_end].strip()
                # Clean up the title (take first 80 chars max)
                chapter_title = chapter_title[:80].strip()
                chapter_boundaries.append((page_num, chapter_title))
                break  # Only detect one chapter per page
    
    if not chapter_boundaries:
        # No chapters detected - treat entire PDF as one unit
        all_pages = [p["page_number"] for p in pages]
        return {"Complete": all_pages}
    
    # Build chapter -> pages mapping
    chapters = {}
    for i, (start_page, title) in enumerate(chapter_boundaries):
        if i + 1 < len(chapter_boundaries):
            end_page = chapter_boundaries[i + 1][0] - 1
        else:
            end_page = len(pages)
        
        page_range = list(range(start_page, end_page + 1))
        chapters[title] = page_range
    
    # Handle pages before the first chapter
    first_chapter_page = chapter_boundaries[0][0]
    if first_chapter_page > 1:
        preface_pages = list(range(1, first_chapter_page))
        chapters["Preface"] = preface_pages
    
    return chapters


def chunk_text(text: str) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + settings.CHUNK_SIZE
        chunks.append(text[start:end])
        start += settings.CHUNK_SIZE - settings.CHUNK_OVERLAP
    return [c for c in chunks if c.strip()]


def create_embedding(text: str) -> List[float]:
    """Create an embedding for the given text."""
    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def ingest_pdf(file_path: str, pdf_name: str, username: str) -> Dict:
    """Ingest a PDF: extract pages, detect chapters, create embeddings, store everything.
    
    Returns dict with ingestion stats.
    """
    # Extract text page by page
    pages = extract_pages(file_path)
    total_pages = len(pages)
    print(f"✅ Extracted {total_pages} pages from PDF")
    
    # Validate meaningful text
    total_text = "".join(p["text"] for p in pages)
    if len(total_text.strip()) < 100:
        error_msg = f"PDF contains insufficient text ({len(total_text)} chars). This might be an image-based PDF or encrypted document."
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # Detect chapters
    chapters = detect_chapters(pages)
    chapter_names = [name for name in chapters.keys() if name != "Complete"]
    print(f"✅ Detected {len(chapter_names)} chapters: {chapter_names}")
    
    # Build a reverse mapping: page_number -> chapter_name
    page_to_chapter = {}
    for chapter_name, page_nums in chapters.items():
        for pn in page_nums:
            page_to_chapter[pn] = chapter_name
    
    # Create embeddings and store in vector DB
    all_ids = []
    all_embeddings = []
    all_documents = []
    all_metadatas = []
    
    for page in pages:
        page_num = page["page_number"]
        page_text = page["text"]
        
        if not page_text.strip():
            continue
        
        chapter_name = page_to_chapter.get(page_num, "Unknown")
        chunks = chunk_text(page_text)
        
        for chunk_idx, chunk in enumerate(chunks):
            emb = create_embedding(chunk)
            chunk_id = f"page{page_num}_chunk{chunk_idx}"
            
            all_ids.append(chunk_id)
            all_embeddings.append(emb)
            all_documents.append(chunk)
            all_metadatas.append({
                "page_number": page_num,
                "chapter": chapter_name,
                "chunk_index": chunk_idx,
            })
    
    if not all_embeddings:
        error_msg = "No valid text chunks found to create embeddings"
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    print(f"✅ Generated {len(all_embeddings)} embeddings")
    
    # Store in per-PDF collection
    vector_store.add_documents(
        pdf_name=pdf_name,
        ids=all_ids,
        documents=all_documents,
        embeddings=all_embeddings,
        metadatas=all_metadatas,
    )
    print(f"✅ Stored {len(all_documents)} chunks in collection '{pdf_name}'")
    
    # Store metadata in JSON registry
    metadata_store.add_pdf(
        name=pdf_name,
        username=username,
        filename=file_path.split("/")[-1],
        total_pages=total_pages,
        chapters=chapter_names if chapter_names else ["Complete"],
    )
    print(f"✅ Registered PDF '{pdf_name}' in metadata store")
    
    return {
        "total_pages": total_pages,
        "chapters_found": chapter_names if chapter_names else ["Complete"],
        "total_chunks": len(all_documents),
    }
