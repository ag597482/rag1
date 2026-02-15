from typing import Optional, Dict, Any
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


def retrieve_context(
    pdf_name: str,
    question: str,
    top_k: Optional[int] = None,
    where: Optional[Dict[str, Any]] = None,
) -> str:
    """Retrieve relevant context from a specific PDF's vector store.
    
    Args:
        pdf_name: The unique name of the PDF to query.
        question: The question to find relevant context for.
        top_k: Number of results to return (defaults to settings.TOP_K).
        where: Optional metadata filter (e.g., {"page_number": 5}).
    """
    try:
        if top_k is None:
            top_k = settings.TOP_K
            
        question_embedding = create_embedding(question)
        results = vector_store.query(
            pdf_name=pdf_name,
            embedding=question_embedding,
            top_k=top_k,
            where=where,
        )
        
        documents = results["documents"]
        print(f"📝 Retrieved {len(documents)} results from '{pdf_name}' collection")
        
        if not documents or all(not d.strip() for d in documents):
            print("⚠️ No relevant documents found")
            return ""
        
        context = "\n\n".join(documents)
        print(f"✅ Context length: {len(context)} characters")
        return context
    except Exception as e:
        print(f"❌ Error during retrieval: {e}")
        return ""


def get_content_by_page(pdf_name: str, page_number: int) -> str:
    """Get all document chunks for a specific page of a PDF."""
    try:
        results = vector_store.get_documents_by_metadata(
            pdf_name=pdf_name,
            where={"page_number": page_number},
        )
        documents = results["documents"]
        if not documents:
            return ""
        return "\n".join(documents)
    except Exception as e:
        print(f"❌ Error getting page content: {e}")
        return ""


def get_content_by_chapter(pdf_name: str, chapter: str) -> str:
    """Get all document chunks for a specific chapter of a PDF."""
    try:
        results = vector_store.get_documents_by_metadata(
            pdf_name=pdf_name,
            where={"chapter": chapter},
        )
        documents = results["documents"]
        if not documents:
            return ""
        return "\n".join(documents)
    except Exception as e:
        print(f"❌ Error getting chapter content: {e}")
        return ""


def get_all_content(pdf_name: str) -> str:
    """Get all document chunks for the entire PDF."""
    try:
        results = vector_store.get_all_documents(pdf_name=pdf_name)
        documents = results["documents"]
        if not documents:
            return ""
        return "\n".join(documents)
    except Exception as e:
        print(f"❌ Error getting all content: {e}")
        return ""
