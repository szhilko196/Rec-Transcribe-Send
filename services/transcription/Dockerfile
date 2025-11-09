# Transcription Service Dockerfile
# Speech transcription (Faster-Whisper) + speaker diarization (pyannote.audio)

ARG BASE_IMAGE=python:3.10-slim-bookworm
FROM ${BASE_IMAGE}

# Metadata
LABEL maintainer="Meeting Transcriber Team"
LABEL description="Transcription service with Faster-Whisper and pyannote.audio"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    build-essential \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY transcribe.py .
COPY diarize.py .

# Create directories for data and models
RUN mkdir -p /app/data/audio \
    /app/data/transcripts \
    /app/models/whisper \
    /app/models/pyannote \
    /app/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
