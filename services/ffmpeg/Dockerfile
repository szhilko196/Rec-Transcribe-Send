# FFmpeg Service Dockerfile
# Extracts audio from video files for subsequent transcription

FROM python:3.10-slim

# Metadata
LABEL maintainer="Meeting Transcriber Team"
LABEL description="FFmpeg service for audio extraction from video files"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Create directories for data
RUN mkdir -p /app/data/input /app/data/audio

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
