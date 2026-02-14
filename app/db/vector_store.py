import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

class VectorStore:
    def __init__(self):
        self.client = chromadb.Client(
            ChromaSettings(persist_directory=settings.CHROMA_DIR)
        )
        self.collection = self.client.get_or_create_collection("documents")

    def add_documents(self, ids, documents, embeddings, metadatas=None):
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def query(self, embedding, top_k):
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k
        )
        return results["documents"][0]
