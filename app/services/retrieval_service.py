from openai import OpenAI
from app.core.config import settings
from app.db.vector_store import VectorStore

client = OpenAI()
vector_store = VectorStore()


def create_embedding(text: str):
    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def retrieve_context(question: str):
    question_embedding = create_embedding(question)
    results = vector_store.query(question_embedding, settings.TOP_K)
    return "\n\n".join(results)
