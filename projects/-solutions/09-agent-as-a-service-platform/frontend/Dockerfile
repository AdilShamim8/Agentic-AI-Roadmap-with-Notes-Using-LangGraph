# =============================================================================
# Frontend (Next.js) Dockerfile — dev mode with hot reload
# =============================================================================
FROM node:20-alpine

WORKDIR /app

# Copy package.json + lockfile first for better layer caching
COPY package.json package-lock.json* ./

# Install deps (will be re-run in compose command if needed)
RUN npm install

# Copy source (mounted as volume in compose, so this is just for image builds)
COPY . .

EXPOSE 3000

# Default command — overridden in compose
CMD ["npm", "run", "dev"]
