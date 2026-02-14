from fastapi import APIRouter
from pydantic import BaseModel
from app.services.retrieval_service import retrieve_context
from app.services.llm_service import generate_answer

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str

@router.post("/ask")
async def ask_question(request: QuestionRequest):
    context = retrieve_context(request.question)
    answer = generate_answer(request.question, context)
    return {"answer": answer}
