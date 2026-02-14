from fastapi import FastAPI
from app.routes import upload, ask

app = FastAPI(title="RAG Service")

app.include_router(upload.router)
app.include_router(ask.router)

@app.get("/health")
def health():
    return {"status": "ok"}
