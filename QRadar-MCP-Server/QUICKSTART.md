# QRadar MCP Server - Quick Start Guide

## What is This?

A containerized MCP (Model Context Protocol) server that lets Claude Desktop interact with IBM QRadar SIEM through natural language.

---

## 🚀 One-Command Setup

### Step 1: Pull the Container

```bash
docker pull ghcr.io/addanuj/qradar-mcp-server:latest
```

### Step 2: Configure Claude Desktop

Edit your Claude Desktop config file:

**Mac/Linux:**
```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
notepad %APPDATA%\Claude\claude_desktop_config.json
```

**Paste this configuration:**
```json
{
  "mcpServers": {
    "qradar": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "QRADAR_HOST=https://your-qradar-server.com",
        "-e",
        "QRADAR_API_TOKEN=your-api-token-here",
        "ghcr.io/addanuj/qradar-mcp-server:latest"
      ]
    }
  }
}
```

### Step 3: Restart Claude Desktop

Quit Claude completely and reopen it.

---

## 📋 What You Can Do

Once connected, ask Claude things like:

- **"List all QRadar offenses"**
- **"Get QRadar system information"**
- **"Show me high severity offenses from the last 24 hours"**
- **"Get details for offense ID 123"**
- **"List all QRadar users"**

Claude will automatically use the QRadar MCP server to execute these requests.

---

## 🔧 Available Tools

The server provides 4 main tools:

1. **qradar_discover** - Discover available QRadar API endpoints (728 total)
2. **qradar_get** - Fetch data from QRadar (offenses, users, assets, etc.)
3. **qradar_post** - Create or update QRadar resources
4. **qradar_delete** - Delete QRadar resources

These tools cover 100% of the QRadar API v26.0 specification.

---

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `QRADAR_HOST` | QRadar console URL | `https://qradar.example.com` |
| `QRADAR_API_TOKEN` | QRadar SEC token | `your-api-token` |

### Getting Your QRadar API Token

1. Log into QRadar Console
2. Go to **Admin** → **Authorized Services**
3. Create a new service token
4. Copy the token (it won't be shown again!)

---

## 🐳 Container Details

- **Image:** `ghcr.io/addanuj/qradar-mcp-server:latest`
- **Size:** 35.8 MB (compressed), 150 MB (disk)
- **Base:** Python 3.11 Alpine Linux
- **Registry:** GitHub Container Registry (ghcr.io)
- **Source:** https://github.ibm.com/ashrivastava/QRadar-MCP-Server

---

## 🔍 Troubleshooting

### Claude doesn't show QRadar tools

**Check if container is running:**
```bash
docker ps | grep qradar-mcp-server
```

**Check Claude logs:**
```bash
tail -50 ~/Library/Logs/Claude/mcp-server-qradar.log
```

**Look for:** `QRadar MCP Server - 4 tools, 728 endpoints`

### Connection errors

**Verify QRadar is accessible:**
```bash
curl -k https://your-qradar-server.com/api/system/about
```

**Test the container manually:**
```bash
docker run --rm \
  -e QRADAR_HOST=https://your-qradar-server.com \
  -e QRADAR_API_TOKEN=your-token \
  ghcr.io/addanuj/qradar-mcp-server:latest \
  python3 -c "print('✅ Container works!')"
```

### Pull latest version

```bash
docker pull ghcr.io/addanuj/qradar-mcp-server:latest
```

---

## 📚 Examples

### List Open Offenses
Ask Claude: **"Show me all open offenses with severity greater than 5"**

### Get User Information
Ask Claude: **"List all QRadar users and their roles"**

### Search Events
Ask Claude: **"Search for failed login events in the last hour"**

### Asset Management
Ask Claude: **"Show me all assets in the default domain"**

---

## 🔐 Security Notes

- API tokens are passed as environment variables (not stored in the container)
- Container runs with `--rm` flag (auto-deleted after use)
- No persistent data is stored
- All communication uses HTTPS

---

## 📞 Support

- **GitHub Issues:** https://github.ibm.com/ashrivastava/QRadar-MCP-Server/issues
- **IBM QRadar API Docs:** https://www.ibm.com/docs/en/qradar-common

---

## ✅ Success Checklist

- [ ] Docker installed and running
- [ ] QRadar API token obtained
- [ ] Claude Desktop config updated
- [ ] Claude Desktop restarted
- [ ] Asked Claude about QRadar tools
- [ ] Successfully queried QRadar data

**Everything working? You're all set! 🎉**
