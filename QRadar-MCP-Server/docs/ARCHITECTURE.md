# QRadar MCP Server - Architecture

## Overview

The QRadar MCP Server uses **4 generic tools** to provide access to all **728 QRadar API endpoints** via containerized deployment.

---

## The 4 Tools

| Tool | Purpose |
|------|---------|
| `qradar_get` | Fetch data (GET requests) |
| `qradar_post` | Create/Update resources (POST requests) |
| `qradar_delete` | Delete resources (DELETE requests) |
| `qradar_discover` | Find endpoints + parameters dynamically |

---

## Container Architecture

**Base:** `python:3.12-alpine`  
**Size:** 35.8 MB compressed  
**Registry:** `ghcr.io/addanuj/qradar-mcp-server:latest`

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QRADAR_HOST` | ✅ Yes | - | QRadar console URL |
| `QRADAR_API_TOKEN` | ✅ Yes | - | QRadar SEC token |
| `QRADAR_VERIFY_SSL` | ❌ No | `false` | SSL certificate verification |

---

## Tool Details

### qradar_discover
Find QRadar API endpoints dynamically.

**Parameters:**
- `search` (string, required) - Search term
- `method` (string, optional) - HTTP method filter
- `limit` (integer, optional) - Max results (default: 10)

### qradar_get
Fetch data from QRadar (GET requests).

**Parameters:**
- `endpoint` (string, required) - API path (e.g., "/siem/offenses")
- `params` (object, optional) - Query parameters

### qradar_post
Create or modify resources (POST requests).

**Parameters:**
- `endpoint` (string, required) - API path
- `params` (object, optional) - Query parameters
- `body` (object, optional) - Request body

### qradar_delete
Remove resources (DELETE requests).

**Parameters:**
- `endpoint` (string, required) - API path with resource ID

---

## Summary

- **Tools:** 4
- **Endpoints:** 728
- **Deployment:** Docker/Podman container
- **Protocol:** MCP (Model Context Protocol)
