# QRadar MCP Server

MCP server providing Claude Desktop with access to all 728 QRadar API endpoints through 4 generic tools.

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

## Architecture

### Token Efficiency

**Why 4 Tools = 728 Endpoints:**
- <span style="color: red">Traditional approach: 728 individual tools = ~500,000+ tokens per message</span>
- <span style="color: green">Our approach: 4 generic tools = ~1,000 tokens per message</span>
- **Result:** 500x more efficient token usage

Every MCP request includes all tool definitions. With 4 tools instead of 728, Claude can access the full QRadar API without overwhelming token budgets.

### The 4 Tools

| Tool | Purpose | Coverage |
|------|---------|----------|
| `qradar_discover` | Find endpoints dynamically | All 728 endpoints |
| `qradar_get` | Fetch data (GET) | 414 endpoints |
| `qradar_post` | Create/update (POST) | 227 endpoints |
| `qradar_delete` | Delete resources (DELETE) | 87 endpoints |

### How It Works

1. **Discover** - Claude searches for endpoints by keyword
2. **Execute** - Claude calls the appropriate generic tool
3. **Dynamic** - No hardcoded endpoint list needed

**Example Flow:**
```
User: "Show me all offenses"
→ Claude knows QRadar offenses API
→ Calls: qradar_get(endpoint="/siem/offenses")
→ Returns: QRadar offense data
```

---

## Usage Examples

| Category | Example Query | What It Does |
|----------|---------------|--------------|
| **Offenses** | "Show me all open offenses" | Lists active security incidents |
| | "Get offense details for ID 123" | Retrieves specific offense information |
| | "Find high severity offenses from last 24 hours" | Filters critical recent threats |
| **Assets** | "List all assets in my network" | Shows discovered network devices |
| | "Get asset details for IP 192.168.1.100" | Retrieves specific asset information |
| **Reference Data** | "Create a reference set for blocked IPs" | Creates new threat intelligence collection |
| | "Add 10.0.0.1 to blocked_ips reference set" | Updates threat intelligence data |
| **Users & Access** | "List all QRadar users" | Shows user accounts and roles |
| | "Get user details for admin account" | Retrieves user permissions |
| **AQL Queries** | "Search for failed login events" | Executes Ariel query language search |
| | "Find events from source IP 192.168.1.50" | Searches event data by criteria |
| **System Info** | "Get QRadar system information" | Shows version, license, and status |
| | "Check QRadar health status" | Monitors system health |

---

## Project Structure

```
QRadar-MCP-Server/
├── container/
│   └── Dockerfile
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── client.py
│   ├── server.py
│   └── tools.py
├── pyproject.toml
└── README.md
```

---

## Container Details

- **Registry:** `ghcr.io/addanuj/qradar-mcp-server:latest`
- **Protocol:** MCP (Model Context Protocol)
- **API Version:** QRadar v26.0
