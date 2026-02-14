import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Model Configuration
    MODEL_NAME = "gpt-4o-mini"
    EMBEDDING_MODEL = "text-embedding-3-small"
    
    # Chunking Configuration
    CHUNK_SIZE = 700
    CHUNK_OVERLAP = 100
    
    # Retrieval Configuration
    TOP_K = 3
    TEMPERATURE = 0.2
    
    # Database Configuration
    CHROMA_DIR = "./chroma_db"

settings = Settings()
