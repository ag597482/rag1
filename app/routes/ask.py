from fastapi import APIRouter, HTTPException
from app.models.schemas import AskRequest, AskResponse
from app.services.retrieval_service import retrieve_context
from app.services.llm_service import generate_answer
from app.db.metadata_store import MetadataStore

router = APIRouter()
metadata_store = MetadataStore()


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question about a specific uploaded PDF."""
    # Validate PDF exists
    pdf_meta = metadata_store.get_pdf(request.pdf)
    if not pdf_meta:
        raise HTTPException(
            status_code=404,
            detail=f"PDF '{request.pdf}' not found. Use GET /pdfs to see available PDFs.",
        )

    print(f"❓ Question for '{request.pdf}': {request.question}")
    context = retrieve_context(pdf_name=request.pdf, question=request.question)

    if not context or not context.strip():
        print("⚠️ No context found, returning default message")
        return AskResponse(
            answer="No relevant content found in this PDF for your question.",
            context_found=False,
            pdf=request.pdf,
        )

    print(f"✅ Generating answer with {len(context)} chars of context")
    answer = generate_answer(request.question, context)
    return AskResponse(
        answer=answer,
        context_found=True,
        pdf=request.pdf,
    )
