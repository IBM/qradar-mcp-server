# QRadar MCP Server

MCP server providing Claude Desktop with access to all 728 QRadar API endpoints through 4 tools.

---

## Quick Start

### Pull Image
```bash
podman pull ghcr.io/addanuj/qradar-mcp-server:latest
```

### Create Container
```bash
podman run -d --name qradar-mcp-server \
  -e QRADAR_HOST="https://your-qradar.com" \
  -e QRADAR_API_TOKEN="your-token" \
  ghcr.io/addanuj/qradar-mcp-server:latest
```

### Configure Claude Desktop
`~/Library/Application Support/Claude/claude_desktop_config.json`
```json
{
  "mcpServers": {
    "qradar": {
      "command": "/opt/podman/bin/podman",
      "args": ["exec", "-i", "qradar-mcp-server", "python", "-m", "src.server"]
    }
  }
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QRADAR_HOST` | ✅ Yes | - | QRadar console URL |
| `QRADAR_API_TOKEN` | ✅ Yes | - | QRadar SEC token |
| `QRADAR_VERIFY_SSL` | No | `false` | SSL verification |

---

## Tools

| Tool | Purpose |
|------|---------|
| `qradar_discover` | Find endpoints |
| `qradar_get` | Fetch data |
| `qradar_post` | Create/update resources |
| `qradar_delete` | Delete resources |

**Total Coverage:** 728 QRadar API v26.0 endpoints

---

## Project Structure

```
QRadar-MCP-Server/
├── container/
│   └── Dockerfile
├── docs/
│   ├── ARCHITECTURE.md
│   └── README.md
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── client.py
│   ├── server.py
│   └── tools.py
└── pyproject.toml
```

---

## Container Details

- **Registry:** `ghcr.io/addanuj/qradar-mcp-server:latest`
- **Protocol:** MCP (Model Context Protocol)

---

## Usage Examples

Ask Claude:
- "List all QRadar offenses"
- "Get QRadar system information"
- "Show me high severity offenses"
- "Create a reference set"
