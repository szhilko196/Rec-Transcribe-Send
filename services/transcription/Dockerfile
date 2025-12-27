# Transcription Service Dockerfile
# Speech transcription (Faster-Whisper) + speaker diarization (pyannote.audio)

ARG BASE_IMAGE=python:3.10-slim-bookworm
FROM ${BASE_IMAGE}

# Metadata
LABEL maintainer="Meeting Transcriber Team"
LABEL description="Transcription service with Faster-Whisper and pyannote.audio with CUDA support"

# Install system dependencies
# For CUDA base images, we need to install Python and all dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
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
    wget \
    && rm -rf /var/lib/apt/lists/*

# Note: cuDNN is provided by the base image (nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04)
# PyTorch 2.4.1+cu121 is built against cuDNN 8, so this is the correct version

# Create symbolic links for python and pip (CUDA base images need this)
RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

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

# Set LD_LIBRARY_PATH to include cuDNN 9 libraries
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:$LD_LIBRARY_PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI application
# Set timeout to 4 hours (14400s) to handle very long transcriptions
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info", "--timeout-keep-alive", "14400"]
