from pypdf import PdfReader
from openai import OpenAI
from app.core.config import settings
from app.db.vector_store import VectorStore

client = OpenAI(api_key=settings.OPENAI_API_KEY)
vector_store = VectorStore()


def extract_text(file_path: str):
    """Extract text from PDF, with fallback to OCR for image-based PDFs"""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    # If very little text was extracted, try OCR
    if len(text.strip()) < 100:
        print("⚠️ Little text extracted with pypdf, attempting OCR...")
        try:
            from app.services.ocr_service import extract_text_with_ocr
            text = extract_text_with_ocr(file_path)
        except ImportError as e:
            print(f"⚠️ OCR not available: {e}")
        except Exception as e:
            print(f"⚠️ OCR failed: {e}")
    
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
    try:
        text = extract_text(file_path)
        print(f"✅ Extracted {len(text)} characters from PDF")
        
        # Validate that we extracted meaningful text
        if len(text.strip()) < 100:
            error_msg = f"PDF contains insufficient text ({len(text)} chars). This might be an image-based PDF or encrypted document."
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        chunks = chunk_text(text)
        print(f"✅ Created {len(chunks)} chunks")

        ids = []
        embeddings = []
        documents = []

        for i, chunk in enumerate(chunks):
            if chunk.strip():  # Only process non-empty chunks
                emb = create_embedding(chunk)
                ids.append(f"chunk_{i}")
                embeddings.append(emb)
                documents.append(chunk)

        if not embeddings:
            error_msg = "No valid text chunks found to create embeddings"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        print(f"✅ Generated {len(embeddings)} embeddings")
        vector_store.add_documents(ids, documents, embeddings)
        print(f"✅ Successfully stored {len(documents)} documents in vector store")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        raise
