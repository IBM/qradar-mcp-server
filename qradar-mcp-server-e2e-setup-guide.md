# QRadar MCP Server — End-to-End Setup Guide for IBM Bob

This guide takes you from zero to a working IBM Bob + QRadar MCP integration.
Two roles are involved — an **Admin** who sets up the server once, and **Users** who configure their Bob client.

---

## Prerequisites

### Admin needs

| Requirement | Details |
|-------------|---------|
| A Linux server with Docker | Any machine reachable from the user's network. Does **not** need to be the QRadar console itself. |
| QRadar Console with API access | Admin → Authorized Services → create/copy a token |
| Port 8001 open | In the Docker host's firewall / security group |

### User needs

| Requirement | Details |
|-------------|---------|
| IBM Bob installed | Cloud desktop or desktop app |
| Server URL | Provided by the admin after setup (e.g., `http://10.0.0.5:8001/sse`) |
| API key | Provided by the admin (the `MCP_API_KEY` value) |

---

## Part A: Server Setup (Admin — one time)

### A1. Obtain a QRadar API Token

Log into the QRadar Console and create an Authorized Service token:

1. Open **QRadar Console → Admin → Authorized Services**
2. Click **Add Authorized Service**
3. Give it a name (e.g., `mcp-server`) and select the required permissions
4. Click **Create** and copy the token

Save this token — you need it in step A3.

---

### A2. Pull the Container Image

SSH into the machine that will host the MCP server:

```bash
ssh root@<mcp-server-host>
docker pull ghcr.io/ibm/qradar-mcp-server:latest
```

The image supports both `linux/amd64` and `linux/arm64`.

---

### A3. Run the Container

```bash
docker run -d \
  --name qradar-mcp \
  --restart unless-stopped \
  -p 8001:8001 \
  -e QRADAR_HOST="https://<qradar-console>" \
  -e QRADAR_API_TOKEN="<from-step-A1>" \
  -e QRADAR_VERIFY_SSL="false" \
  -e MCP_API_KEY="$(openssl rand -hex 32)" \
  ghcr.io/ibm/qradar-mcp-server:latest
```

**What each parameter does:**

| Parameter | Purpose |
|-----------|---------|
| `-p 8001:8001` | Exposes the MCP SSE transport on port 8001 |
| `QRADAR_HOST` | Full URL of the QRadar console (e.g., `https://qradar.example.com`) |
| `QRADAR_API_TOKEN` | Authorized Service token from step A1 — used server-side to call QRadar APIs |
| `QRADAR_VERIFY_SSL` | Set to `true` if the QRadar console has a valid TLS certificate |
| `MCP_API_KEY` | Shared secret that MCP clients must present to connect. The `openssl rand -hex 32` command generates a random 64-character hex string. |

> **Tip:** Record the generated `MCP_API_KEY` immediately. Run `docker inspect qradar-mcp | grep MCP_API_KEY` to retrieve it later if needed.

> **Security note:** Users never see the QRadar API token. The MCP server holds it server-side and attaches it to every QRadar API call automatically. Users only authenticate to the MCP server itself via the `MCP_API_KEY`.

---

### A4. Verify the Server is Running

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{
  "status": "healthy",
  "mode": "http",
  "tools": 4,
  "endpoints": 728,
  "auth_required": true,
  "oauth_enabled": false
}
```

- `auth_required: true` — API key enforcement is active (because `MCP_API_KEY` is set)
- `tools: 4` — all four QRadar tools are loaded (`qradar_get`, `qradar_execute`, `qradar_delete`, `qradar_discover`)
- `endpoints: 728` — full QRadar REST API coverage

---

### A5. Share Credentials with Each User

Send each user (over a secure channel — encrypted email, Slack DM, or in person):

1. The **server URL**: `http://<mcp-server-host>:8001/sse`
2. The **API key**: the 64-character hex string generated in step A3

---

## Part B: Client Setup — IBM Bob (Each User)

### What you need from the admin

1. **Server URL** — e.g., `http://9.30.147.112:8001/sse`
2. **API key** — the 64-character hex string the admin generated for you

---

### B1. Bob's MCP Settings File Location

Bob stores all MCP server configurations in a single JSON file:

| Operating System | File Path |
|-----------------|-----------|
| **macOS** | `~/Library/Application Support/IBM Bob/User/globalStorage/ibm.bob-code/settings/mcp_settings.json` |
| **Linux** | `~/.config/IBM Bob/User/globalStorage/ibm.bob-code/settings/mcp_settings.json` |
| **Windows** | `%APPDATA%\IBM Bob\User\globalStorage\ibm.bob-code\settings\mcp_settings.json` |

---

### B2. Option A — Ask Bob to Configure Itself (Recommended)

You can paste this prompt directly into Bob and it will write the settings file for you:

```
I want to configure the QRadar MCP server in my IBM Bob settings.

Please update my MCP settings file at:
~/Library/Application Support/IBM Bob/User/globalStorage/ibm.bob-code/settings/mcp_settings.json

Add the following MCP server entry (do not remove any existing entries):

Server name: qradar-mcp-server
Type: sse
URL: http://<mcp-server-host>:8001/sse
Authorization header: Bearer <your-api-key>
alwaysAllow: ["qradar_get", "qradar_execute", "qradar_delete", "qradar_discover"]

After writing the file, tell me what you changed and remind me to restart Bob.
```

Bob will read the file, add the entry, save it, and tell you to restart.

---

### B3. Option B — Configure Manually

Open the settings file (create it if it doesn't exist) and add the `qradar-mcp-server` block:

```json
{
  "mcpServers": {
    "qradar-mcp-server": {
      "type": "sse",
      "url": "http://<mcp-server-host>:8001/sse",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      },
      "alwaysAllow": ["qradar_get", "qradar_execute", "qradar_delete", "qradar_discover"]
    }
  }
}
```

> If the file already has other MCP servers, add the `qradar-mcp-server` block inside the existing `mcpServers` object — do **not** replace the whole file.

**Restart Bob** after saving.

---

### B4. VS Code (GitHub Copilot)

Add to `.vscode/mcp.json` in your project root:

```json
{
  "servers": {
    "qradar-mcp-server": {
      "type": "sse",
      "url": "http://<mcp-server-host>:8001/sse",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}
```

Reload VS Code (`Cmd+Shift+P` → **Reload Window**).

---

### B5. Claude Desktop (stdio mode)

Claude Desktop runs the container locally in stdio mode — no network server needed. Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "qradar": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "QRADAR_HOST=https://<qradar-console>",
        "-e", "QRADAR_API_TOKEN=<your-qradar-token>",
        "-e", "QRADAR_VERIFY_SSL=false",
        "ghcr.io/ibm/qradar-mcp-server:latest",
        "--stdio"
      ]
    }
  }
}
```

> **Note:** In stdio mode the user runs the process locally and supplies their own QRadar token directly. No `MCP_API_KEY` is needed — QRadar's own authentication (the `SEC` header) is the security gate.

---

### B6. Verify the Connection

After restarting your client, ask:

> *"Use the QRadar MCP server to discover available API endpoints for offenses"*

Expected: The assistant calls `qradar_discover` and returns a list of QRadar SIEM offense endpoints.

---

## Part C: Bootstrap Query — Ask Bob to Read This Guide and Set Itself Up

If you share this guide file with someone, they can give Bob this single prompt to do the entire client setup automatically:

```
Please read the file at:
~/code/QRadar-MCP-Server/qradar-mcp-server-e2e-setup-guide.md

Then configure my IBM Bob MCP settings for the QRadar MCP server as described
in the "Option A — Ask Bob to Configure Itself" section (Part B2).

My server URL is: http://<mcp-server-host>:8001/sse
My API key is: <your-api-key>

Use the alwaysAllow list from the guide. Do not remove any existing
MCP server entries. After writing the file, show me what changed
and tell me to restart Bob.
```

Bob will read this guide, find the correct JSON structure, write the settings file, and instruct you to restart.

---

## Part D: What You Can Ask After Setup

You never need QRadar credentials in your prompts. The MCP server authenticates to QRadar internally.

| Task | Example prompt |
|------|----------------|
| Recent threats | *"Show me the top 10 open offenses"* |
| Browse APIs | *"What QRadar API endpoints are available for offense management?"* |
| Offense details | *"Get offense 42 with all its notes and contributing events"* |
| Event search | *"Search for failed login events from external IPs in the last hour"* |
| Asset inventory | *"What assets are in my network inventory?"* |
| Reference data | *"List all reference sets and show me the contents of 'blocked_ips'"* |
| Add to blocklist | *"Add 192.168.1.100 to the suspicious IPs reference set"* |
| AQL query | *"Create an Ariel AQL search for DNS queries to suspicious domains"* |
| Active rules | *"List all active custom rules"* |
| System health | *"What is the current system health status?"* |
| Log sources | *"List all configured log sources"* |
| User management | *"List all QRadar users and their roles"* |

---

## Part E: Key Rotation (Admin)

The `MCP_API_KEY` is a static value set as an environment variable. To rotate it:

### Step 1: Generate a new key

```bash
NEW_KEY=$(openssl rand -hex 32)
echo "New API key: $NEW_KEY"
```

### Step 2: Restart the container with the new key

```bash
docker rm -f qradar-mcp

docker run -d \
  --name qradar-mcp \
  --restart unless-stopped \
  -p 8001:8001 \
  -e QRADAR_HOST="https://<qradar-console>" \
  -e QRADAR_API_TOKEN="<your-qradar-token>" \
  -e QRADAR_VERIFY_SSL="false" \
  -e MCP_API_KEY="$NEW_KEY" \
  ghcr.io/ibm/qradar-mcp-server:latest
```

### Step 3: Distribute the new key

Send the new key to all users over a secure channel. Each user must update the `Authorization` header in their client config (replace the old key with the new one) and restart their client.

> **Tip:** The old key stops working **immediately** when the container restarts — coordinate with your users before rotating.
