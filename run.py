#!/usr/bin/env python
"""
Entry point to run the RAG FastAPI application.
This file can be run directly with: python run.py
Or use the play button in your IDE on this file.
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("🚀 Starting RAG Service...")
    print(f"📍 Server will be available at: http://127.0.0.1:8000")
    print(f"📚 API Documentation: http://127.0.0.1:8000/docs")
    print(f"🏥 Health Check: http://127.0.0.1:8000/health")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
