from fastapi import APIRouter, UploadFile, File
import shutil
import os
from app.services.ingestion_service import ingest_pdf
from app.core.config import settings

router = APIRouter()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    # Create docs directory if it doesn't exist
    os.makedirs(settings.DOCS_DIR, exist_ok=True)
    
    # Save file to docs folder
    file_path = os.path.join(settings.DOCS_DIR, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ingest_pdf(file_path)

        return {
            "message": "PDF ingested successfully",
            "filename": file.filename,
            "path": file_path
        }
    except ValueError as e:
        # Return user-friendly error for validation issues
        return {
            "message": "Upload failed",
            "error": str(e),
            "filename": file.filename,
            "suggestion": "Please ensure the PDF is text-based and not an image-only/scanned document."
        }
    except Exception as e:
        # Return error for other issues
        return {
            "message": "Upload failed",
            "error": str(e),
            "filename": file.filename
        }
