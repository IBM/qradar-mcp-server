# QRadar MCP Server — Setup Guide

Complete step-by-step instructions to deploy the MCP server, onboard clients, and manage API keys.

Two roles are involved:

| Role | Responsibility | Requires |
|------|---------------|----------|
| **MCP Server Admin** | Deploys the container, configures env vars, generates/revokes API keys | SSH to MCP server host |
| **Client (end user)** | Pastes API key + URL into their AI assistant config, starts chatting | Just the key and the URL |

---

## Part A: Server Setup (Admin — one time)

### A1. Pull the Container

SSH into the machine that will host the MCP server (this can be any server with Docker — it does not need to be the QRadar server itself):

```bash
ssh root@<mcp-server-host>
docker pull ghcr.io/ibm/qradar-mcp-server:latest
```

The image supports both `linux/amd64` and `linux/arm64`.

---

### A2. Run the Container

```bash
docker run -d \
  --name qradar-mcp-server \
  --restart unless-stopped \
  -p 8001:8001 \
  -e QRADAR_HOST="https://<your-qradar-console>" \
  -e QRADAR_API_TOKEN="<your-qradar-sec-token>" \
  -e QRADAR_VERIFY_SSL="false" \
  -e MCP_API_KEY="<generate-a-strong-random-key>" \
  ghcr.io/ibm/qradar-mcp-server:latest
```

What each part does:

| Flag | Purpose |
|------|---------|
| `-p 8001:8001` | Exposes the SSE transport on port 8001 |
| `QRADAR_HOST` | Base URL of your QRadar console (e.g., `https://qradar.example.com`) |
| `QRADAR_API_TOKEN` | QRadar authorized service token — get it from: QRadar Console → Admin → Authorized Services → Add |
| `QRADAR_VERIFY_SSL` | Set to `false` for self-signed certs, `true` for production |
| `MCP_API_KEY` | Shared secret clients must send as `Authorization: Bearer <key>` |

> **Generating a strong `MCP_API_KEY`:**
>
> ```bash
> openssl rand -base64 32
> ```
>
> Copy the output — this is your `MCP_API_KEY`. Keep it secret; share only with authorized clients.

See the [Configuration Reference](README.md#configuration) in the README for all optional variables (API version, timeout, etc.).

---

### A3. Verify the Server

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
  "auth_required": true
}
```

Confirm:

- `auth_required: true` — API key validation is active
- `endpoints: 728` — all QRadar API endpoints discovered
- `tools: 4` — all 4 MCP tools registered

---

### A4. Share Access with Clients

Send clients:

1. **Server URL** — `http://<mcp-server-host>:8001/sse`
2. **API Key** — the value you set as `MCP_API_KEY`

Share the key securely (encrypted email, Slack DM — never a public channel).

---

## Part B: Client Setup (Each User)

You need two things from the admin:

1. **Server URL** — e.g., `http://9.30.147.112:8001/sse`
2. **API Key** — the shared key configured on the server

### B1. Configure Your AI Assistant

#### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Restart Claude Desktop.

---

#### IBM Bob (Cloud Desktop)

Edit `~/Library/Application Support/IBM Bob/User/globalStorage/ibm.bob-code/settings/mcp_settings.json`:

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

Restart Bob.

---

### B2. Verify the Connection

After restarting your AI assistant, try this prompt:

> "Use qradar_discover to list all available QRadar API categories"

You should see categories like: SIEM, Assets, Analytics, Ariel, Reference Data, Config, System.

---

### B3. Start Chatting with QRadar

You can now use natural language to interact with QRadar. Example prompts:

| Task | Prompt |
|------|--------|
| Browse APIs | "What endpoints are available for offense management?" |
| Get offenses | "Show me the top 10 open offenses" |
| Search events | "Search for failed login events in the last hour using AQL" |
| List assets | "What assets are in my network inventory?" |
| Run a search | "Create an Ariel search for DNS queries to suspicious domains" |
| Check rules | "List all active custom rules in QRadar" |
| Reference sets | "Show all entries in the suspicious IPs reference set" |

You don't need QRadar credentials in your prompts. The MCP server handles authentication using the `QRADAR_API_TOKEN` configured by the admin on the server side. Your API key only proves you're authorized to talk to the MCP server.

---

## Part C: Key Rotation & Revocation (Admin)

Since `MCP_API_KEY` is a single shared key configured as an environment variable, rotation requires restarting the container with a new key value:

### C1. Generate a New Key

```bash
openssl rand -base64 32
# Example output: 7vX+mK2nPqR8sT1uW3yZ5aB0cD4eF6gH9iJ2kL=
```

### C2. Update the Container

```bash
# Stop and remove the old container
docker stop qradar-mcp-server && docker rm qradar-mcp-server

# Start with new key
docker run -d \
  --name qradar-mcp-server \
  --restart unless-stopped \
  -p 8001:8001 \
  -e QRADAR_HOST="https://<your-qradar-console>" \
  -e QRADAR_API_TOKEN="<your-qradar-sec-token>" \
  -e QRADAR_VERIFY_SSL="false" \
  -e MCP_API_KEY="<new-key>" \
  ghcr.io/ibm/qradar-mcp-server:latest
```

All clients using the old key will immediately get `401 Unauthorized`.

### C3. Client: Update Config

Clients must replace the old key in their AI assistant config, then reload.

### When to Rotate Keys

| Situation | Action |
|-----------|--------|
| Key compromised or leaked | Rotate immediately (C1 → C2 → C3) |
| Scheduled rotation | Generate new key (C1), update clients (C3), restart server (C2) |
| User leaves the team | Rotate and issue new key to remaining users |

---

## Running from Source (Alternative)

If you prefer not to use Docker, run the MCP server directly with Python 3.10+:

```bash
git clone https://github.com/IBM/qradar-mcp-server.git
cd qradar-mcp-server
pip install -e .

export QRADAR_HOST=https://<your-qradar-console>
export QRADAR_API_TOKEN=<your-sec-token>
export QRADAR_VERIFY_SSL=false
export MCP_API_KEY=<your-api-key>

python -m src
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 Unauthorized` on SSE connect | Missing or wrong API key | Check `Authorization: Bearer <key>` header in your AI assistant config |
| `{"status": "healthy", "auth_required": false}` | `MCP_API_KEY` not set | Restart container with `-e MCP_API_KEY="<key>"` |
| `endpoints: 0` in health response | QRadar host unreachable | Verify `QRADAR_HOST` and network connectivity |
| `Connection refused on port 8001` | Container not running | Check `docker ps` and `docker logs qradar-mcp-server` |
| SSL errors | Self-signed cert on QRadar | Set `QRADAR_VERIFY_SSL=false` |
| `qradar_get` returns empty results | Wrong endpoint path | Use `qradar_discover` first to find the correct path |
| AQL search hangs | QRadar search still running | Call `qradar_get` on `/ariel/searches/<search_id>` to poll status |

---

## Quick Reference

```
Admin: ssh root@<mcp-server-host>

Health check:   curl http://localhost:8001/health
Container logs: docker logs qradar-mcp-server --tail 50
Restart:        docker restart qradar-mcp-server

Generate key:   openssl rand -base64 32
```
