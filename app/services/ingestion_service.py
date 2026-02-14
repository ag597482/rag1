from pypdf import PdfReader
from openai import OpenAI
from app.core.config import settings
from app.db.vector_store import VectorStore

client = OpenAI(api_key=settings.OPENAI_API_KEY)
vector_store = VectorStore()


def extract_text(file_path: str):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def chunk_text(text: str):
    chunks = []
    start = 0
    while start < len(text):
        end = start + settings.CHUNK_SIZE
        chunks.append(text[start:end])
        start += settings.CHUNK_SIZE - settings.CHUNK_OVERLAP
    return chunks


def create_embedding(text: str):
    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def ingest_pdf(file_path: str):
    text = extract_text(file_path)
    chunks = chunk_text(text)

    ids = []
    embeddings = []

    for i, chunk in enumerate(chunks):
        emb = create_embedding(chunk)
        ids.append(f"chunk_{i}")
        embeddings.append(emb)

    vector_store.add_documents(ids, chunks, embeddings)
