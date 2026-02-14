from fastapi import APIRouter
from pydantic import BaseModel
from app.services.retrieval_service import retrieve_context
from app.services.llm_service import generate_answer

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str

@router.post("/ask")
async def ask_question(request: QuestionRequest):
    print(f"❓ Question received: {request.question}")
    context = retrieve_context(request.question)
    
    if not context or not context.strip():
        print("⚠️ No context found, returning default message")
        return {
            "answer": "No relevant documents found in the database. Please upload documents first.",
            "context_found": False
        }
    
    print(f"✅ Generating answer with {len(context)} chars of context")
    answer = generate_answer(request.question, context)
    return {
        "answer": answer,
        "context_found": True,
        "sources_used": True
    }
