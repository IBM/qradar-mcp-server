# QRadar MCP Server - Dual Mode Container (stdio + HTTP)
FROM python:3.12-alpine

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

# Expose HTTP port (used when running with --http)
EXPOSE 8001

# Default: stdio mode (for Claude Desktop)
# Use: --http for HTTP/SSE mode (for containers/web)
ENTRYPOINT ["python", "-m", "src.server"]
