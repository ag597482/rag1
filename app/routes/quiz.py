from fastapi import APIRouter, HTTPException
from app.models.schemas import QuizRequest, QuizResponse, QuizQuestion, QuizType
from app.services.quiz_service import generate_complete_quiz, generate_chapter_quiz
from app.db.metadata_store import MetadataStore, fuzzy_match_chapter

router = APIRouter()
metadata_store = MetadataStore()


@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """Generate a quiz to test understanding of a PDF.
    
    - type "complete": generates quiz covering the entire PDF
    - type "chapter": requires chapter name — generates quiz for a specific chapter/unit
      (fuzzy matching: "lecture 1" will match "Lecture #1: Intro to OS")
    """
    # Validate PDF exists
    pdf_meta = metadata_store.get_pdf(request.pdf)
    if not pdf_meta:
        raise HTTPException(
            status_code=404,
            detail=f"PDF '{request.pdf}' not found. Use GET /pdfs to see available PDFs.",
        )

    num_questions = request.num_questions or 10

    if request.type == QuizType.COMPLETE:
        questions_data = generate_complete_quiz(request.pdf, num_questions)

    elif request.type == QuizType.CHAPTER:
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
        questions_data = generate_chapter_quiz(
            request.pdf, matched_chapter, num_questions
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid quiz type.")

    if not questions_data:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate quiz questions. Please try again.",
        )

    # Convert to QuizQuestion models
    questions = [
        QuizQuestion(
            type=q["type"],
            question=q["question"],
            options=q.get("options"),
            answer=q["answer"],
            explanation=q["explanation"],
        )
        for q in questions_data
    ]

    return QuizResponse(
        pdf=request.pdf,
        type=request.type.value,
        questions=questions,
    )
