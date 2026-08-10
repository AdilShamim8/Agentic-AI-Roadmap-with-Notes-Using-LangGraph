# =============================================================================
# Shared base Dockerfile for all A2A services
# =============================================================================
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better layer caching
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project source
COPY . .

# Install the project itself in development mode
RUN pip install --no-cache-dir -e .

# Default environment
ENV LLM_BACKEND=mock \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

# Default command (overridden by docker-compose per service)
CMD ["python", "-c", "print('Override CMD in docker-compose.yml')"]
