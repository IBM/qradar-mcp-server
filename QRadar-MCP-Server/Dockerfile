# QRadar MCP Server - Optimized Container for Claude Desktop
FROM python:3.12-alpine

LABEL org.opencontainers.image.source=https://github.ibm.com/ashrivastava/QRadar-MCP-Server
LABEL org.opencontainers.image.description="QRadar MCP Server for Claude Desktop"

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

# MCP runs via stdio
ENTRYPOINT ["python", "-m", "src.server"]
