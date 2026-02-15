from fastapi import FastAPI
from app.routes import upload, ask, pdfs, summary, quiz

app = FastAPI(
    title="Book Summarizer & Quiz Generator",
    description="Upload PDFs, get page/chapter summaries, ask questions, and generate quizzes.",
    version="2.0.0",
)

app.include_router(upload.router, tags=["Upload"])
app.include_router(pdfs.router, tags=["PDFs"])
app.include_router(ask.router, tags=["Ask"])
app.include_router(summary.router, tags=["Summary"])
app.include_router(quiz.router, tags=["Quiz"])


@app.get("/health")
def health():
    return {"status": "ok"}
