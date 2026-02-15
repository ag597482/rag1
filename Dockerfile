FROM python:3.13-slim

# Install system dependencies for OCR (optional) and general use
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create the persistent data directory
RUN mkdir -p /data/docs /data/chroma_db

# Expose the port (Railway sets PORT env var)
EXPOSE 8000

# Run the app — Railway provides PORT env var
CMD ["python", "run.py"]
