from fastapi import APIRouter, HTTPException
from app.db.metadata_store import MetadataStore
from app.db.vector_store import VectorStore

router = APIRouter()
metadata_store = MetadataStore()
vector_store = VectorStore()


@router.get("/pdfs")
async def list_pdfs():
    """List all uploaded PDFs with their metadata."""
    pdfs = metadata_store.list_pdfs()
    return {
        "total": len(pdfs),
        "pdfs": [
            {
                "name": pdf["name"],
                "uploaded_by": pdf["uploaded_by"],
                "total_pages": pdf["total_pages"],
                "chapters": pdf["chapters"],
                "upload_date": pdf["upload_date"],
            }
            for pdf in pdfs
        ],
    }


@router.delete("/pdfs/{name}")
async def delete_pdf(name: str):
    """Delete a PDF's metadata and its vector store collection."""
    pdf_meta = metadata_store.get_pdf(name)
    if not pdf_meta:
        raise HTTPException(
            status_code=404,
            detail=f"PDF '{name}' not found.",
        )

    # Delete the ChromaDB collection
    vector_store.delete_collection(name)

    # Delete from metadata JSON
    metadata_store.delete_pdf(name)

    return {
        "message": f"PDF '{name}' deleted successfully.",
        "name": name,
    }
