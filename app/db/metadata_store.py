import json
import os
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.config import settings


def fuzzy_match_chapter(query: str, chapters: List[str]) -> Optional[str]:
    """Find the best matching chapter name using flexible matching.
    
    Tries in order:
    1. Exact match
    2. Case-insensitive match
    3. Normalized match (strip special chars like #, -, :)
    4. Substring/partial match (e.g. "lecture 1" matches "Lecture #1: Intro to OS")
    
    Returns the actual chapter name from the list, or None if no match.
    """
    if not query or not chapters:
        return None

    # 1. Exact match
    if query in chapters:
        return query

    query_lower = query.lower().strip()

    # 2. Case-insensitive exact match
    for ch in chapters:
        if ch.lower().strip() == query_lower:
            return ch

    # Helper: normalize a string by removing special chars and extra spaces
    def normalize(s: str) -> str:
        s = re.sub(r"[#:\-–—.,;()\[\]{}]", " ", s.lower())
        return re.sub(r"\s+", " ", s).strip()

    query_norm = normalize(query)

    # 3. Normalized exact match
    for ch in chapters:
        if normalize(ch) == query_norm:
            return ch

    # 4. Substring / partial match — check if user query is contained in chapter name
    for ch in chapters:
        if query_norm in normalize(ch):
            return ch

    # 5. Reverse: chapter name contained in query
    for ch in chapters:
        if normalize(ch) in query_norm:
            return ch

    # 6. Match by number extraction — e.g. "lecture 1" matches "Lecture #1: Intro"
    query_nums = re.findall(r"\d+", query)
    query_words = set(re.findall(r"[a-z]+", query_lower))
    if query_nums:
        for ch in chapters:
            ch_nums = re.findall(r"\d+", ch)
            ch_words = set(re.findall(r"[a-z]+", ch.lower()))
            # Same number AND at least one keyword in common
            if query_nums[0] in ch_nums and query_words & ch_words:
                return ch

    return None


class MetadataStore:
    """JSON-based metadata store for tracking uploaded PDFs."""

    def __init__(self):
        self.file_path = settings.METADATA_FILE
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the metadata JSON file if it doesn't exist."""
        if not os.path.exists(self.file_path):
            self._write_data({"pdfs": []})

    def _read_data(self) -> Dict[str, Any]:
        """Read the entire metadata file."""
        with open(self.file_path, "r") as f:
            return json.load(f)

    def _write_data(self, data: Dict[str, Any]):
        """Write data to the metadata file."""
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def name_exists(self, name: str) -> bool:
        """Check if a PDF with the given name already exists."""
        data = self._read_data()
        return any(pdf["name"] == name for pdf in data["pdfs"])

    def add_pdf(
        self,
        name: str,
        username: str,
        filename: str,
        total_pages: int,
        chapters: List[str],
    ) -> Dict[str, Any]:
        """Register a new PDF in the metadata store."""
        data = self._read_data()

        pdf_entry = {
            "name": name,
            "uploaded_by": username,
            "filename": filename,
            "total_pages": total_pages,
            "chapters": chapters,
            "upload_date": datetime.now().isoformat(),
        }

        data["pdfs"].append(pdf_entry)
        self._write_data(data)
        return pdf_entry

    def list_pdfs(self) -> List[Dict[str, Any]]:
        """List all uploaded PDFs."""
        data = self._read_data()
        return data["pdfs"]

    def get_pdf(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific PDF's metadata by name."""
        data = self._read_data()
        for pdf in data["pdfs"]:
            if pdf["name"] == name:
                return pdf
        return None

    def delete_pdf(self, name: str) -> bool:
        """Remove a PDF from the metadata store."""
        data = self._read_data()
        original_count = len(data["pdfs"])
        data["pdfs"] = [pdf for pdf in data["pdfs"] if pdf["name"] != name]
        if len(data["pdfs"]) < original_count:
            self._write_data(data)
            return True
        return False
