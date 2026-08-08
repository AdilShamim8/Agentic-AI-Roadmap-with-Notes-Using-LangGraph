# syntax=docker/dockerfile:1.7
# ---- Base image ----
# Python 3.11 slim with system deps for PyMuPDF, Pillow, ChromaDB.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    DATA_DIR=/data

# System deps: build-essential for compiling any wheels that lack binaries,
# libglib/libgl for PIL/PyMuPDF runtime, nodejs for the z-ai SDK CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libgl1 \
        libsm6 \
        libxrender1 \
        libxext6 \
        curl \
        ca-certificates \
        gnupg \
        git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (for the z-ai-web-dev-sdk CLI).
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g z-ai-web-dev-sdk \
    && ln -sf $(which z-ai) /usr/local/bin/z-ai || true

WORKDIR /app

# Install Python deps first (better layer caching).
COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source.
COPY src ./src
COPY scripts ./scripts
COPY samples ./samples
COPY README.md ./
COPY .env.example ./

# Install the package itself.
RUN pip install -e . --no-deps

# Persistent data dir.
RUN mkdir -p /data /opt/hf-cache
VOLUME ["/data"]

# Default to the API server. Override with `python -m doc_analyst.cli web` etc.
EXPOSE 8000 8501
CMD ["python", "-m", "doc_analyst.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
