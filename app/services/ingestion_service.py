import re
from typing import List, Dict, Tuple, Optional
from pypdf import PdfReader
from openai import OpenAI
from app.core.config import settings
from app.db.vector_store import VectorStore
from app.db.metadata_store import MetadataStore

client = OpenAI(api_key=settings.OPENAI_API_KEY)
vector_store = VectorStore()
metadata_store = MetadataStore()

# Primary division keywords for book-style chapters (used for main "Chapters" list).
# Only these are used so we don't mix in "Section 18.19" or TOC lines.
PRIMARY_DIVISION_KEYWORDS = ["chapter", "part", "unit"]

# All division keywords (for fallback when no primary divisions found)
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

# Only consider a match as a chapter start if it appears in the first N chars of the page.
# This avoids treating Table of Contents entries as chapter starts (they appear mid-page).
# Allows chapter titles that appear after a graphic or margin (e.g. NCERT-style textbooks).
# TOC pages are skipped entirely, so this only applies to real content pages.
CHAPTER_HEADING_MAX_OFFSET = 1500

# Prose indicators: if the "chapter" line contains these, it's likely body text, not a heading.
CHAPTER_PROSE_INDICATORS = re.compile(
    r"\b(that|which|who|when|we|you|they|this|these|there|here|"
    r"is|are|was|were|does|do|did|has|have|had|will|would|can|could|"
    r"does not|do not|did not|is not|are not)\b",
    re.I,
)

def _build_chapter_patterns(keywords: List[str]) -> List[str]:
    """Build flexible regex patterns for given division keywords."""
    patterns = []
    for kw in keywords:
        patterns.append(rf"(?im)^{kw}\s*[#:\-–—]?\s*\d+")
        patterns.append(rf"(?im)^{kw}\s*[#:\-–—]?\s*({NUMBER_WORDS})")
    return patterns

# Primary patterns: only chapter, part, unit — so "Section 18.19" won't appear as a chapter.
CHAPTER_PATTERNS = _build_chapter_patterns(PRIMARY_DIVISION_KEYWORDS)
# Fallback patterns if no primary divisions found (e.g. course slides with "Lecture 1")
FALLBACK_CHAPTER_PATTERNS = _build_chapter_patterns(DIVISION_KEYWORDS)


def extract_pages(file_path: str) -> List[Dict]:
    """Extract text from PDF page by page.
    
    Returns a list of dicts: [{page_number: int, text: str}, ...]
    """
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        page_num = i + 1

        # If this page has very little text (e.g. image/scan), run OCR on this page only
        if len(text.strip()) < 20:
            try:
                from app.services.ocr_service import (
                    OCR_AVAILABLE,
                    extract_text_from_page_with_ocr,
                )
                if OCR_AVAILABLE:
                    ocr_text = extract_text_from_page_with_ocr(file_path, page_num)
                    if ocr_text:
                        text = ocr_text
                        print(f"✅ OCR extracted {len(text)} chars from page {page_num}")
            except (ImportError, Exception) as e:
                print(f"⚠️ Single-page OCR failed for page {page_num}: {e}")

        pages.append({
            "page_number": page_num,
            "text": text,
        })

    # Fallback: if whole file has almost no text, run OCR on entire PDF
    total_text = "".join(p["text"] for p in pages)
    if len(total_text.strip()) < 100:
        print("⚠️ Little text extracted with pypdf, attempting full-file OCR...")
        try:
            from app.services.ocr_service import extract_text_with_ocr
            ocr_text = extract_text_with_ocr(file_path)
            ocr_pages = ocr_text.split("\n--- Page ")
            for j, ocr_page in enumerate(ocr_pages):
                if j == 0 and not ocr_page.strip():
                    continue
                page_idx = j - 1 if j > 0 else 0
                if page_idx < len(pages):
                    clean_text = re.sub(r"^\d+\s*---\n?", "", ocr_page)
                    pages[page_idx]["text"] = clean_text
        except (ImportError, Exception) as e:
            print(f"⚠️ OCR not available or failed: {e}")

    return pages


def _extract_division_number(title: str) -> Optional[int]:
    """Extract numeric part from 'Chapter 1', 'Part 2', etc. for deduplication."""
    m = re.search(r"(?:chapter|part|unit)\s*[#:\-–—]?\s*(\d+)", title, re.I)
    return int(m.group(1)) if m else None


def _looks_like_chapter_heading(line: str) -> bool:
    """True if the line looks like a real chapter heading, not body text.
    Rejects e.g. 'Chapter 16 that the moon does not' (prose) and accepts
    e.g. 'Chapter 16. Light' or 'Chapter 16 — CROP PRODUCTION'.
    """
    if not line or len(line) > 200:
        return False
    # Reject if it contains prose-style words (sentence, not title)
    if CHAPTER_PROSE_INDICATORS.search(line):
        return False
    # After "Chapter N" we expect: optional punctuation, then title (capital/uppercase) or end.
    # So "Chapter 16. Light" or "Chapter 16  Light" or "Chapter 16" alone is ok.
    # "Chapter 16 that..." has "that" (lowercase) right after number -> reject already by prose.
    # Also reject if the rest of the line is mostly lowercase (sentence).
    after_match = re.search(r"(?:chapter|part|unit)\s*[#:\-–—]?\s*\d+\s*[.\-–—:]?\s*(.+)", line, re.I)
    if after_match:
        rest = after_match.group(1).strip()
        if len(rest) > 3 and rest[0].islower():
            return False
    return True


def _is_likely_toc_page(text: str, patterns: List[str]) -> bool:
    """True if page has many division headings (likely Table of Contents)."""
    # Count total matches (e.g. "Chapter 1", "Chapter 2" ... each match the same pattern)
    count = sum(len(re.findall(p, text)) for p in patterns)
    return count >= 4


# Pattern to extract "Chapter N" - flexible (no ^) so we catch TOC when "Chapter" and "2" span lines
_CHAPTER_NUM_PATTERN_TOC = re.compile(r"chapter\s*(\d+)\b", re.I)


def _parse_toc_chapter_numbers(pages: List[Dict], patterns: List[str]) -> List[int]:
    """From TOC pages, extract ordered list of chapter numbers (e.g. [1,2,...,18])."""
    # Collect (num, page_num, pos) from all TOC pages so we can sort by position
    hits: List[Tuple[int, int, int]] = []
    for page in pages:
        if not _is_likely_toc_page(page["text"], patterns):
            continue
        for m in _CHAPTER_NUM_PATTERN_TOC.finditer(page["text"]):
            hits.append((int(m.group(1)), page["page_number"], m.start()))
    if not hits:
        return []
    # Sort by page then position; then unique by chapter number preserving order
    hits.sort(key=lambda x: (x[1], x[2]))
    seen: Dict[int, None] = {}
    ordered = []
    for num, _pn, _pos in hits:
        if num not in seen:
            seen[num] = None
            ordered.append(num)
    return ordered


def _find_candidates_for_chapter(
    pages: List[Dict],
    chapter_num: int,
    patterns: List[str],
    toc_page_numbers: Optional[set] = None,
) -> List[Tuple[int, str, int]]:
    """Find all (page_num, title, position) where 'Chapter N' looks like a heading.
    Searches full page text; matches 'Chapter N' even when not at start of line.
    """
    toc_page_numbers = toc_page_numbers or set()
    # Match "Chapter N" anywhere (no ^) so we catch titles after graphics or wrapped lines
    pattern = re.compile(rf"chapter\s+{chapter_num}\b", re.I)
    candidates = []
    for page in pages:
        text = page["text"]
        page_num = page["page_number"]
        for m in pattern.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            if line_end == -1:
                line_end = min(m.end() + 100, len(text))
            line = text[line_start:line_end].strip()[:80]
            if not _looks_like_chapter_heading(line):
                continue
            candidates.append((page_num, line, m.start()))
    return candidates


def _pick_best_chapter_start(
    candidates: List[Tuple[int, str, int]], toc_page_numbers: set
) -> Optional[Tuple[int, str, int]]:
    """Prefer: not on TOC page, then match near top of page (pos < offset), then min pos, then max page."""
    if not candidates:
        return None
    def key(c: Tuple[int, str, int]) -> Tuple[int, int, int, int]:
        page_num, title, pos = c
        on_toc = 1 if page_num in toc_page_numbers else 0
        in_top = 0 if pos < CHAPTER_HEADING_MAX_OFFSET else 1
        return (on_toc, in_top, pos, -page_num)
    return min(candidates, key=key)


def detect_chapters(pages: List[Dict]) -> Dict[str, List[int]]:
    """Detect chapter/unit boundaries from page texts.
    
    - If TOC pages exist, parses them for chapter numbers (1..18) then finds each
      chapter's start page by scanning all pages for a heading-like "Chapter N" line.
    - Otherwise uses first-N-chars scan and dedup by chapter number.
    """
    toc_page_nums = {
        p["page_number"] for p in pages
        if _is_likely_toc_page(p["text"], CHAPTER_PATTERNS)
    }
    toc_numbers = _parse_toc_chapter_numbers(pages, CHAPTER_PATTERNS)

    chapter_boundaries: List[Tuple[int, str]] = []
    if len(toc_numbers) >= 3:
        # TOC-driven: for each chapter number, find best start page (full-page search)
        for num in toc_numbers:
            candidates = _find_candidates_for_chapter(
                pages, num, CHAPTER_PATTERNS, toc_page_nums
            )
            best = _pick_best_chapter_start(candidates, toc_page_nums)
            if best:
                chapter_boundaries.append((best[0], best[1]))
        if not chapter_boundaries:
            toc_numbers = []
    else:
        toc_numbers = []

    if not toc_numbers or not chapter_boundaries:
        # Fallback: collect boundaries from first CHAPTER_HEADING_MAX_OFFSET chars per page
        def _collect_boundaries(patterns: List[str]) -> List[Tuple[int, str, int]]:
            raw = []
            for page in pages:
                text = page["text"]
                page_num = page["page_number"]
                if _is_likely_toc_page(text, patterns):
                    continue
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match and match.start() < CHAPTER_HEADING_MAX_OFFSET:
                        line_start = text.rfind("\n", 0, match.start()) + 1
                        line_end = text.find("\n", match.end())
                        if line_end == -1:
                            line_end = min(match.end() + 100, len(text))
                        chapter_title = text[line_start:line_end].strip()[:80]
                        if not _looks_like_chapter_heading(chapter_title):
                            continue
                        raw.append((page_num, chapter_title, match.start()))
                        break
            return raw

        raw_boundaries = _collect_boundaries(CHAPTER_PATTERNS)
        if not raw_boundaries:
            raw_boundaries = _collect_boundaries(FALLBACK_CHAPTER_PATTERNS)
        if not raw_boundaries:
            all_pages = [p["page_number"] for p in pages]
            return {"Complete": all_pages}

        numbered: Dict[int, Tuple[int, str, int]] = {}
        unnumbered: List[Tuple[int, str, int]] = []
        for page_num, title, pos in raw_boundaries:
            num = _extract_division_number(title)
            if num is None:
                unnumbered.append((page_num, title, pos))
                continue
            if num not in numbered:
                numbered[num] = (page_num, title, pos)
            else:
                _p, _t, existing_pos = numbered[num]
                if pos < existing_pos or (pos == existing_pos and page_num > _p):
                    numbered[num] = (page_num, title, pos)
        all_entries = [(p, t) for (p, t, _) in unnumbered]
        for num in sorted(numbered.keys()):
            all_entries.append((numbered[num][0], numbered[num][1]))
        all_entries.sort(key=lambda x: x[0])
        chapter_boundaries = all_entries

    # Build chapter -> pages mapping
    chapters = {}
    for i, (start_page, title) in enumerate(chapter_boundaries):
        if i + 1 < len(chapter_boundaries):
            end_page = chapter_boundaries[i + 1][0] - 1
        else:
            end_page = len(pages)
        page_range = list(range(start_page, end_page + 1))
        chapters[title] = page_range

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
