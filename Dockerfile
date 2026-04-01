FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
COPY README.md .
RUN pip install --no-cache-dir .

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/qradar-mcp-server /usr/local/bin/qradar-mcp-server
COPY src/ src/
EXPOSE 8001
CMD ["qradar-mcp-server", "--transport", "streamable-http", "--port", "8001"]
