from fastapi import APIRouter, UploadFile, File
import shutil
from app.services.ingestion_service import ingest_pdf

router = APIRouter()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ingest_pdf(file_path)

    return {"message": "PDF ingested successfully"}
