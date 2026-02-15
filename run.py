#!/usr/bin/env python
"""
Entry point to run the RAG FastAPI application.
This file can be run directly with: python run.py
Or use the play button in your IDE on this file.
"""
import os
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    # Railway sets PORT env var; default to 8000 for local dev
    port = int(os.getenv("PORT", 8000))
    # Use 0.0.0.0 in production (containers), 127.0.0.1 for local dev
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RAILWAY_ENVIRONMENT") is None  # Only reload locally

    print("🚀 Starting RAG Service...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"🏥 Health Check: http://{host}:{port}/health")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
