from openai import OpenAI
from app.core.config import settings
from app.db.vector_store import VectorStore

client = OpenAI(api_key=settings.OPENAI_API_KEY)
vector_store = VectorStore()


def create_embedding(text: str):
    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def retrieve_context(question: str):
    try:
        question_embedding = create_embedding(question)
        results = vector_store.query(question_embedding, settings.TOP_K)
        print(f"📝 Retrieved {len(results)} results from vector store")
        print(f"📄 Results: {results[:2] if results else 'EMPTY'}")  # Print first 2 for debugging
        
        if not results or all(not r.strip() for r in results):
            print("⚠️ No relevant documents found in vector store")
            return ""
            
        context = "\n\n".join(results)
        print(f"✅ Context length: {len(context)} characters")
        return context
    except Exception as e:
        print(f"❌ Error during retrieval: {e}")
        return ""
