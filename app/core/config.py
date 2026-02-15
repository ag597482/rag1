import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Model Configuration
    MODEL_NAME = "gpt-5.2"
    EMBEDDING_MODEL = "text-embedding-3-small"
    
    # Chunking Configuration
    CHUNK_SIZE = 700
    CHUNK_OVERLAP = 100
    
    # Retrieval Configuration
    TOP_K = 3
    TEMPERATURE = 0.2
    
    # Data directory — on Railway, set DATA_DIR=/data via env var
    # Locally it defaults to current directory
    DATA_DIR = os.getenv("DATA_DIR", ".")

    # Database Configuration
    CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
    
    # Upload Configuration
    DOCS_DIR = os.path.join(DATA_DIR, "docs")
    
    # Metadata Configuration
    METADATA_FILE = os.path.join(DATA_DIR, "pdf_metadata.json")

settings = Settings()
