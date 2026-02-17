"""
QRadar MCP Tools - 4 Tools for 728 Endpoints (Improved)

Improvements:
1. qradar_discover returns detailed schema with body fields
2. qradar_execute validates endpoint exists BEFORE calling
3. Better categorization (CREATE vs UPDATE vs LIST)
4. No guessing - tool tells exactly what's available
"""

from typing import Any
from mcp.types import Tool

from .client import QRadarClient
from .discovery import (
    categorize_endpoint,
    parse_parameters,
    format_endpoint,
    paths_match,
    _endpoint_cache,
)


TOOLS: list[Tool] = [
    Tool(
        name="qradar_get",
        description="""
Fetch data from QRadar. Use for listing or retrieving resources.

Examples:
- List offenses: endpoint="/siem/offenses"
- Get offense: endpoint="/siem/offenses/123"
- Filter: endpoint="/siem/offenses", filter="status=OPEN"
- List users: endpoint="/config/access/users"
- System info: endpoint="/system/about"
""",
        inputSchema={
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "API path"},
                "filter": {"type": "string", "description": "AQL filter"},
                "fields": {"type": "string", "description": "Fields to return"},
                "range": {"type": "string", "description": "Pagination (e.g., 0-49)"},
                "qradar_host": {"type": "string", "description": "QRadar host (optional, overrides env)"},
                "qradar_token": {"type": "string", "description": "API token (optional, overrides env)"},
            },
            "required": ["endpoint"]
        }
    ),

    Tool(
        name="qradar_delete",
        description="""
Delete resources from QRadar.

Examples:
- Delete from reference set: endpoint="/reference_data/sets/blocked_ips/1.2.3.4"
- Delete saved search: endpoint="/ariel/saved_searches/123"
""",
        inputSchema={
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "API path with resource ID"},
                "qradar_host": {"type": "string", "description": "QRadar host (optional, overrides env)"},
                "qradar_token": {"type": "string", "description": "API token (optional, overrides env)"},
            },
            "required": ["endpoint"]
        }
    ),

    Tool(
        name="qradar_discover",
        description="""
Find QRadar API endpoints and get EXACT schema. ALWAYS use this before qradar_execute.

Returns:
- Exact endpoint path (DO NOT GUESS - use exactly what's returned)
- Required parameters with types
- Request body schema if needed

Examples:
- Find user endpoints: search="user", method="POST"
- Find reference data: search="reference_data/sets", method="POST"
""",
        inputSchema={
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search term for path/description"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                "limit": {"type": "integer", "default": 10},
                "qradar_host": {"type": "string", "description": "QRadar host (optional, overrides env)"},
                "qradar_token": {"type": "string", "description": "API token (optional, overrides env)"},
            },
            "required": ["search"]
        }
    ),

    Tool(
        name="qradar_execute",
        description="""
Execute POST/PUT/PATCH requests. ONLY use endpoints returned by qradar_discover.
DO NOT GUESS endpoints - if discover didn't return it, it doesn't exist.

Examples:
- Run AQL: method="POST", endpoint="/ariel/searches", params={"query_expression": "..."}
- Add to set: method="POST", endpoint="/reference_data/sets/{name}", params={"value": "..."}
""",
        inputSchema={
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["POST", "PUT", "PATCH"]},
                "endpoint": {"type": "string", "description": "EXACT path from qradar_discover"},
                "params": {"type": "object", "description": "Query parameters"},
                "body": {"type": "object", "description": "Request body (for BODY type params)"},
                "qradar_host": {"type": "string", "description": "QRadar host (optional, overrides env)"},
                "qradar_token": {"type": "string", "description": "API token (optional, overrides env)"},
            },
            "required": ["method", "endpoint"]
        }
    ),
]


async def execute_tool(client: QRadarClient, name: str, args: dict) -> dict[str, Any]:
    """Execute tool with optional credential override from arguments.
    
    Priority: args credentials > client credentials > environment variables
    """
    # Check if credentials provided in arguments
    qradar_host = args.get("qradar_host")
    qradar_token = args.get("qradar_token")
    
    # If credentials in args, create new client with those credentials
    if qradar_host or qradar_token:
        from .client import QRadarClient
        client = QRadarClient(
            host=qradar_host or client.host,
            api_token=qradar_token or client.api_token,
            verify_ssl=client.verify_ssl,
            timeout=client.timeout
        )
    
    if name == "qradar_get":
        return await _do_get(client, args)
    elif name == "qradar_delete":
        return await _do_delete(client, args)
    elif name == "qradar_discover":
        return await _do_discover(client, args)
    elif name == "qradar_execute":
        return await _do_execute(client, args)
    return {"success": False, "error": f"Unknown tool: {name}"}


async def _do_get(client: QRadarClient, args: dict) -> dict[str, Any]:
    endpoint = args.get("endpoint", "")
    if not endpoint:
        return {"success": False, "error": "endpoint is required"}
    
    params = {}
    if args.get("filter"):
        params["filter"] = args["filter"]
    if args.get("fields"):
        params["fields"] = args["fields"]
    
    return await client.request(
        method="GET",
        endpoint=endpoint,
        params=params if params else None,
        range_header=args.get("range"),
    )


async def _do_delete(client: QRadarClient, args: dict) -> dict[str, Any]:
    endpoint = args.get("endpoint", "")
    if not endpoint:
        return {"success": False, "error": "endpoint is required"}
    
    return await client.request(method="DELETE", endpoint=endpoint)


async def _do_discover(client: QRadarClient, args: dict) -> dict[str, Any]:
    """
    IMPROVED: Returns detailed schema with:
    - Exact endpoint paths
    - All parameters with types
    - Body schema details
    - Clear indication of what's available
    """
    search = args.get("search", "")
    method = args.get("method", "")
    limit = args.get("limit", 10)
    
    if not search:
        return {"success": False, "error": "search term is required"}
    
    # Build filter
    filters = [f"(path ILIKE '%{search}%' OR summary ILIKE '%{search}%')"]
    if method:
        filters.append(f"http_method='{method}'")
    
    result = await client.request(
        method="GET",
        endpoint="/help/endpoints",
        params={"filter": " AND ".join(filters)},
        range_header=f"0-{limit - 1}",
    )
    
    if not result.get("success"):
        return result
    
    endpoints = result.get("data", [])
    
    if not endpoints:
        return {
            "success": True,
            "count": 0,
            "endpoints": [],
            "message": f"NO ENDPOINTS FOUND for search='{search}' method='{method}'. Try different search terms."
        }
    
    # Format with detailed schema using discovery module
    formatted = [format_endpoint(ep) for ep in endpoints]
    
    return {
        "success": True,
        "count": len(formatted),
        "endpoints": formatted,
        "instruction": "Use EXACT paths shown above with qradar_execute. DO NOT modify or guess paths."
    }


async def _do_execute(client: QRadarClient, args: dict) -> dict[str, Any]:
    """
    IMPROVED: Validates endpoint exists before calling.
    """
    method = args.get("method", "").upper()
    endpoint = args.get("endpoint", "")
    params = args.get("params")
    body = args.get("body")
    
    if method not in ["POST", "PUT", "PATCH"]:
        return {"success": False, "error": "method must be POST, PUT, or PATCH"}
    if not endpoint:
        return {"success": False, "error": "endpoint is required"}
    
    # IMPROVEMENT: Validate endpoint exists by checking /help/endpoints
    # Convert endpoint with actual values to pattern (e.g., /users/123 -> /users/{id})
    validation_result = await _validate_endpoint(client, method, endpoint)
    
    if not validation_result["valid"]:
        return {
            "success": False,
            "error": f"ENDPOINT NOT FOUND: {method} {endpoint}",
            "suggestion": validation_result.get("suggestion", "Use qradar_discover to find valid endpoints"),
            "similar_endpoints": validation_result.get("similar", [])
        }
    
    # If body params are required but not provided
    if validation_result.get("requires_body") and not body:
        return {
            "success": False,
            "error": "This endpoint requires a request BODY, not query params",
            "body_schema": validation_result.get("body_sample"),
            "suggestion": "Pass data in 'body' parameter, not 'params'"
        }
    
    return await client.request(
        method=method,
        endpoint=endpoint,
        params=params,
        body=body,
    )


async def _validate_endpoint(client: QRadarClient, method: str, endpoint: str) -> dict:
    """
    Validate that an endpoint exists before calling it.
    Returns validation result with suggestions if not found.
    """
    parts = endpoint.rstrip("/").split("/")
    
    # Try exact match first (for endpoints without path params)
    result = await client.request(
        method="GET",
        endpoint="/help/endpoints",
        params={"filter": f"path='{endpoint}' AND http_method='{method}'"},
        range_header="0-0",
    )
    
    if result.get("success") and result.get("data"):
        ep_data = result["data"][0]
        body_params = [p for p in ep_data.get("parameters", []) if p.get("type") == "BODY"]
        return {
            "valid": True,
            "requires_body": len(body_params) > 0 and body_params[0].get("required", False),
            "body_sample": body_params[0].get("mime_types", [{}])[0].get("sample") if body_params else None
        }
    
    # For endpoints with path params, find matching patterns
    search_bases = []
    if len(parts) >= 3:
        search_bases.append("/".join(parts[:3]))
    if len(parts) >= 2:
        search_bases.append("/".join(parts[:2]))
    
    for base in search_bases:
        result = await client.request(
            method="GET",
            endpoint="/help/endpoints",
            params={"filter": f"path ILIKE '{base}%' AND http_method='{method}'"},
            range_header="0-20",
        )
        
        if result.get("success") and result.get("data"):
            for ep in result["data"]:
                ep_path = ep.get("path", "")
                if paths_match(ep_path, endpoint):
                    body_params = [p for p in ep.get("parameters", []) if p.get("type") == "BODY"]
                    return {
                        "valid": True,
                        "matched_pattern": ep_path,
                        "requires_body": len(body_params) > 0 and body_params[0].get("required", False),
                        "body_sample": body_params[0].get("mime_types", [{}])[0].get("sample") if body_params else None
                    }
    
    # No matches found - suggest similar endpoints
    result = await client.request(
        method="GET",
        endpoint="/help/endpoints",
        params={"filter": f"path ILIKE '%{parts[1] if len(parts) > 1 else endpoint}%' AND http_method='{method}'"},
        range_header="0-5",
    )
    
    if result.get("success") and result.get("data"):
        similar = [{"method": ep.get("http_method"), "path": ep.get("path"), "summary": ep.get("summary", "")} 
                   for ep in result["data"][:3]]
        return {
            "valid": False,
            "suggestion": f"Endpoint {method} {endpoint} does not exist.",
            "similar": similar
        }
    
    base_path = "/".join(parts[:-1]) if len(parts) > 1 else endpoint
    return {
        "valid": False,
        "suggestion": f"No {method} endpoints found matching '{base_path}'. Use qradar_discover to find valid endpoints."
    }
