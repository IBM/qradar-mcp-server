# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder

LABEL org.opencontainers.image.source=https://github.com/addanuj/qradar-mcp-server
LABEL org.opencontainers.image.description="IBM MCP Client - React + FastAPI Web UI for MCP Servers"

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Python Backend + Frontend Static Files
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./app

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Create config directory
RUN mkdir -p /root/.mcp-client

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV CONFIG_DIR=/root/.mcp-client

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
