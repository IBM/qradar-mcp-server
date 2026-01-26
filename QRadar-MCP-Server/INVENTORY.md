# QRadar MCP Project Inventory

**Last Updated:** 2026-01-26

---

## 📦 Container Registry

| Item | Value |
|------|-------|
| **Registry** | GitHub Container Registry (ghcr.io) |
| **Image URL** | `ghcr.io/addanuj/qradar-mcp-server:latest` |
| **Visibility** | Private |
| **Pull Command** | `podman pull ghcr.io/addanuj/qradar-mcp-server:latest` |

---

## 🐳 Container Configuration

| Item | Value |
|------|-------|
| **Container Name** | `qradar-mcp-server` |
| **Runtime** | Podman |
| **Base Image** | `python:3.12-alpine` |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QRADAR_HOST` | ✅ Yes | (empty) | QRadar console URL |
| `QRADAR_API_TOKEN` | ✅ Yes | (empty) | QRadar API token |
| `QRADAR_VERIFY_SSL` | ❌ No | `false` | SSL certificate verification |

---

##  GitHub Repositories

### IBM GitHub (github.ibm.com)

| Repository | URL | Access |
|------------|-----|--------|
| QRadar MCP Server | https://github.ibm.com/ashrivastava/QRadar-MCP-Server | Owner |

---

## ️ MCP Server Details

| Item | Value |
|------|-------|
| **Server Name** | qradar-mcp-server |
| **Version** | 1.26.0 |
| **Tools** | 4 |
| **Endpoints** | 728 |
| **Protocol** | MCP (Model Context Protocol) |

### Available Tools

| Tool | Purpose |
|------|---------|
| `qradar_discover` | Discover available QRadar API endpoints |
| `qradar_get` | Fetch data from QRadar (GET requests) |
| `qradar_post` | Create/update QRadar resources (POST requests) |
| `qradar_delete` | Delete QRadar resources (DELETE requests) |

---

## ⚙️ Claude Desktop Configuration

**File:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "qradar": {
      "command": "/opt/podman/bin/podman",
      "args": [
        "exec",
        "-i",
        "qradar-mcp-server",
        "python",
        "-m",
        "src.server"
      ]
    }
  }
}
```

---

## 🚀 Quick Commands

### Pull Latest Image
```bash
/opt/podman/bin/podman pull ghcr.io/addanuj/qradar-mcp-server:latest
```

### Create Container
```bash
/opt/podman/bin/podman run -d --name qradar-mcp-server \
  -e QRADAR_HOST="https://your-qradar.com" \
  -e QRADAR_API_TOKEN="your-token" \
  -e QRADAR_VERIFY_SSL="false" \
  ghcr.io/addanuj/qradar-mcp-server:latest
```

### Check Container Status
```bash
/opt/podman/bin/podman ps --filter name=qradar-mcp-server
```

### View Container Logs
```bash
/opt/podman/bin/podman logs qradar-mcp-server
```

---

## 📊 Container Registries Inventory

### Check All Containers in Registry
```bash
curl -s -H "Authorization: token YOUR_TOKEN" \
  "https://api.github.com/users/addanuj/packages?package_type=container" | \
  jq -r '.[] | "\(.name) - \(.visibility)"'
```

**Current Count:** 1 container

