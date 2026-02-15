from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import upload, ask, pdfs, summary, quiz

app = FastAPI(
    title="Book Summarizer & Quiz Generator",
    description="Upload PDFs, get page/chapter summaries, ask questions, and generate quizzes.",
    version="2.0.0",
)

# Allow all origins (Flutter web, mobile, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, tags=["Upload"])
app.include_router(pdfs.router, tags=["PDFs"])
app.include_router(ask.router, tags=["Ask"])
app.include_router(summary.router, tags=["Summary"])
app.include_router(quiz.router, tags=["Quiz"])


@app.get("/health")
def health():
    return {"status": "ok"}
