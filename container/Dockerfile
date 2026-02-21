# QRadar MCP Server - Dual Mode Container (stdio + HTTP)
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/IBM/qradar-mcp-server"
LABEL org.opencontainers.image.description="MCP server for IBM QRadar SIEM — AI-driven access to 728+ REST API endpoints via Model Context Protocol. Supports stdio and HTTP/SSE modes with API key authentication."
LABEL org.opencontainers.image.title="QRadar MCP Server"
LABEL org.opencontainers.image.vendor="IBM"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.documentation="https://github.com/IBM/qradar-mcp-server/blob/main/README.md"
LABEL org.opencontainers.image.authors="Anuj Shrivastava (@anujshrivastava15), IBM Security"

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

# Expose HTTP port (used when running with --http)
EXPOSE 8001

# Default: HTTP mode (for containers)
# Use: --stdio for Claude Desktop / local CLI
ENTRYPOINT ["python", "-m", "src"]
