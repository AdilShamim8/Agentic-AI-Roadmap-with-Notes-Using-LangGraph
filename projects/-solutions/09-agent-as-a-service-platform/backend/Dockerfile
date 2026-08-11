# =============================================================================
# Backend Dockerfile — FastAPI app
# =============================================================================
FROM python:3.11-slim

# System deps for psycopg and bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source
COPY . .

EXPOSE 8000

# Default command — overridden in docker-compose to run migrations first
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
