# QRadar MCP Server

MCP server for **IBM QRadar SIEM** — 4 intelligent tools covering all **728 QRadar REST API v26.0 endpoints**.

Instead of creating hundreds of individual tools, this server uses a smart discovery + execution pattern that gives AI assistants full access to the entire QRadar API surface.

## Features

- **4 tools → 728 endpoints** – `qradar_get`, `qradar_delete`, `qradar_discover`, `qradar_execute`
- **API discovery** – Find endpoints by search term, get exact schemas before executing
- **Endpoint validation** – Validates endpoints exist before calling, suggests alternatives
- **Flexible auth** – Credentials via environment variables or per-request override
- **3 transports** – stdio, SSE (deprecated), Streamable HTTP

## Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `qradar_get` | Fetch/list data (GET) | List offenses, get system info |
| `qradar_delete` | Delete resources (DELETE) | Remove from reference sets |
| `qradar_discover` | Find API endpoints & schemas | Search for user endpoints |
| `qradar_execute` | Execute POST/PUT/PATCH | Run AQL queries, create rules |

### Workflow

1. **Discover** – Use `qradar_discover` to find the exact endpoint and required parameters
2. **Execute** – Use the exact path returned by discover with `qradar_get`/`qradar_execute`/`qradar_delete`

## Installation

### Using uvx (recommended)

```bash
uvx qradar-mcp-server --stdio
```

### Using pip

```bash
pip install qradar-mcp-server
qradar-mcp-server --stdio
```

### Using Docker

```bash
docker run -p 8001:8001 \
  -e QRADAR_HOST=https://qradar.example.com \
  -e QRADAR_API_TOKEN=your-token \
  -e MCP_API_KEY=your-mcp-key \
  ghcr.io/ibm/qradar-mcp-server:latest
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QRADAR_HOST` | Yes* | — | QRadar console URL (e.g., `https://qradar.example.com`) |
| `QRADAR_API_TOKEN` | Yes* | — | QRadar authorized service token |
| `QRADAR_API_VERSION` | No | `20.0` | QRadar API version |
| `QRADAR_VERIFY_SSL` | No | `false` | TLS certificate verification |
| `MCP_API_KEY` | HTTP only | — | Bearer token for HTTP transport auth |

\* Can be provided per-request via tool arguments (`qradar_host`, `qradar_token`) instead.

### Claude Desktop (stdio)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "qradar": {
      "command": "uvx",
      "args": ["qradar-mcp-server", "--stdio"],
      "env": {
        "QRADAR_HOST": "https://qradar.example.com",
        "QRADAR_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

### Docker (Streamable HTTP)

```bash
docker run -d \
  -p 8001:8001 \
  -e QRADAR_HOST=https://qradar.example.com \
  -e QRADAR_API_TOKEN=your-token \
  -e MCP_API_KEY=your-mcp-key \
  ghcr.io/ibm/qradar-mcp-server:latest
```

The server exposes:
- `/mcp` — Streamable HTTP MCP endpoint
- `/health` — Health check
- `/tools` — List available tools (REST)
- `/tools/call` — Execute a tool (REST)

## Transport Modes

```bash
# stdio (for Claude Desktop, local CLI)
qradar-mcp-server --stdio

# Streamable HTTP (default, recommended for remote/containers)
qradar-mcp-server --transport streamable-http --port 8001

# SSE (legacy, deprecated)
qradar-mcp-server --transport sse --port 8001
```

## Development

```bash
git clone https://github.com/IBM/qradar-mcp-server.git
cd qradar-mcp-server
pip install -e .
qradar-mcp-server --stdio
```
