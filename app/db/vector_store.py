import chromadb
from typing import List, Optional, Dict, Any
from app.core.config import settings


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DIR)

    def get_collection(self, pdf_name: str):
        """Get or create a collection for a specific PDF."""
        # Sanitize collection name (ChromaDB requires alphanumeric + underscores)
        collection_name = self._sanitize_name(pdf_name)
        return self.client.get_or_create_collection(collection_name)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use as a ChromaDB collection name."""
        sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        # ChromaDB requires collection names between 3 and 63 chars,
        # must start/end with alphanumeric
        sanitized = sanitized.strip("_")
        if len(sanitized) < 3:
            sanitized = sanitized + "_col"
        if len(sanitized) > 63:
            sanitized = sanitized[:63].rstrip("_")
        # Ensure starts and ends with alphanumeric
        if not sanitized[0].isalnum():
            sanitized = "c" + sanitized
        if not sanitized[-1].isalnum():
            sanitized = sanitized + "0"
        return sanitized

    def add_documents(
        self,
        pdf_name: str,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ):
        """Add documents to a PDF-specific collection."""
        collection = self.get_collection(pdf_name)
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        pdf_name: str,
        embedding: List[float],
        top_k: int,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query a PDF-specific collection, optionally filtering by metadata."""
        collection = self.get_collection(pdf_name)
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where
        results = collection.query(**kwargs)
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
        }

    def get_documents_by_metadata(
        self,
        pdf_name: str,
        where: Dict[str, Any],
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get documents from a PDF collection filtered by metadata (e.g., page or chapter)."""
        collection = self.get_collection(pdf_name)
        kwargs = {"where": where}
        if limit:
            kwargs["limit"] = limit
        results = collection.get(**kwargs)
        return {
            "documents": results["documents"] if results["documents"] else [],
            "metadatas": results["metadatas"] if results["metadatas"] else [],
        }

    def get_all_documents(self, pdf_name: str) -> Dict[str, Any]:
        """Get all documents from a PDF collection."""
        collection = self.get_collection(pdf_name)
        results = collection.get()
        return {
            "documents": results["documents"] if results["documents"] else [],
            "metadatas": results["metadatas"] if results["metadatas"] else [],
        }

    def delete_collection(self, pdf_name: str):
        """Delete an entire PDF's collection."""
        collection_name = self._sanitize_name(pdf_name)
        try:
            self.client.delete_collection(collection_name)
        except Exception:
            pass
