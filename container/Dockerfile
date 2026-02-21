# QRadar MCP Server - Dual Mode Container (stdio + HTTP)
FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/IBM/qradar-mcp-server
LABEL org.opencontainers.image.description="QRadar MCP Server - supports stdio and HTTP/SSE modes"

WORKDIR /app

# Copy files
COPY pyproject.toml ./
COPY src/ ./src/

# Install
RUN pip install --no-cache-dir -e .

# Pre-define environment variables (users must set values)
ENV QRADAR_HOST=""
ENV QRADAR_API_TOKEN=""
ENV QRADAR_VERIFY_SSL="false"
ENV MCP_API_KEY=""
ENV OAUTH_JWT_SECRET=""
ENV OAUTH_USERNAME="admin"
ENV OAUTH_PASSWORD=""

# Expose HTTP port (used when running with --http)
EXPOSE 8001

# Default: HTTP mode (for containers)
# Use: --stdio for Claude Desktop / local CLI
ENTRYPOINT ["python", "-m", "src"]
