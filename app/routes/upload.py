from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import os
from app.services.ingestion_service import ingest_pdf
from app.db.metadata_store import MetadataStore
from app.core.config import settings

router = APIRouter()
metadata_store = MetadataStore()


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    name: str = Form(...),
    username: str = Form(...),
):
    """Upload a PDF with a unique name and username.
    
    - file: The PDF file to upload
    - name: A unique name identifier for this PDF
    - username: The user uploading the PDF
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Check if name is unique
    if metadata_store.name_exists(name):
        raise HTTPException(
            status_code=409,
            detail=f"A PDF with the name '{name}' already exists. Please choose a different name.",
        )

    # Create docs directory if it doesn't exist
    os.makedirs(settings.DOCS_DIR, exist_ok=True)

    # Save file to docs folder
    file_path = os.path.join(settings.DOCS_DIR, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ingest with page-wise and chapter-wise processing
        result = ingest_pdf(file_path, pdf_name=name, username=username)

        return {
            "message": "PDF ingested successfully",
            "name": name,
            "pages": result["total_pages"],
            "chapters_found": result["chapters_found"],
            "total_chunks": result["total_chunks"],
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
