from fastapi import APIRouter, HTTPException
from app.models.schemas import SummaryRequest, SummaryResponse, SummaryType
from app.services.summary_service import (
    generate_page_summary,
    generate_complete_summary,
    generate_chapter_summary,
)
from app.db.metadata_store import MetadataStore, fuzzy_match_chapter

router = APIRouter()
metadata_store = MetadataStore()


@router.post("/summary", response_model=SummaryResponse)
async def get_summary(request: SummaryRequest):
    """Generate a summary for a PDF.
    
    - type "page": requires page_number — summarizes a specific page
    - type "complete": summarizes the entire PDF
    - type "chapter": requires chapter name — summarizes a specific chapter/unit
      (fuzzy matching: "lecture 1" will match "Lecture #1: Intro to OS")
    """
    # Validate PDF exists
    pdf_meta = metadata_store.get_pdf(request.pdf)
    if not pdf_meta:
        raise HTTPException(
            status_code=404,
            detail=f"PDF '{request.pdf}' not found. Use GET /pdfs to see available PDFs.",
        )

    if request.type == SummaryType.PAGE:
        if request.page_number is None:
            raise HTTPException(
                status_code=400,
                detail="page_number is required when type is 'page'.",
            )
        if request.page_number < 1 or request.page_number > pdf_meta["total_pages"]:
            raise HTTPException(
                status_code=400,
                detail=f"page_number must be between 1 and {pdf_meta['total_pages']}.",
            )
        summary = generate_page_summary(request.pdf, request.page_number)
        scope = f"Page {request.page_number}"

    elif request.type == SummaryType.COMPLETE:
        summary = generate_complete_summary(request.pdf)
        scope = "Complete Document"

    elif request.type == SummaryType.CHAPTER:
        if not request.chapter:
            raise HTTPException(
                status_code=400,
                detail=f"chapter is required when type is 'chapter'. Available chapters: {pdf_meta['chapters']}",
            )
        # Fuzzy match the chapter name
        matched_chapter = fuzzy_match_chapter(request.chapter, pdf_meta["chapters"])
        if not matched_chapter:
            raise HTTPException(
                status_code=400,
                detail=f"Chapter '{request.chapter}' not found. Available chapters: {pdf_meta['chapters']}",
            )
        summary = generate_chapter_summary(request.pdf, matched_chapter)
        scope = f"Chapter: {matched_chapter}"

    else:
        raise HTTPException(status_code=400, detail="Invalid summary type.")

    return SummaryResponse(
        pdf=request.pdf,
        type=request.type.value,
        summary=summary,
        scope=scope,
    )
