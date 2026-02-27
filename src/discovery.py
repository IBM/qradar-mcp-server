"""
QRadar Endpoint Discovery

Discovers and caches QRadar API endpoints from /help/endpoints.
Used by qradar_discover and qradar_execute tools.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger("qradar-mcp")

# Cache for endpoint validation
_endpoint_cache: dict[str, dict] = {}


def categorize_endpoint(http_method: str, path: str) -> str:
    """Categorize an endpoint by its HTTP method and path pattern."""
    has_path_param = "{" in path

    if http_method == "POST" and not has_path_param:
        return "CREATE"
    elif http_method == "POST" and has_path_param:
        return "UPDATE/ACTION"
    elif http_method == "GET" and has_path_param:
        return "GET_ONE"
    elif http_method == "GET":
        return "LIST"
    elif http_method == "DELETE":
        return "DELETE"
    elif http_method in ["PUT", "PATCH"]:
        return "UPDATE"
    return http_method


def parse_parameters(parameters: list[dict]) -> dict[str, list[dict]]:
    """Parse endpoint parameters into categorized lists."""
    result = {
        "query_params": [],
        "path_params": [],
        "body_params": [],
        "header_params": [],
    }

    for p in parameters:
        param_info = {
            "name": p.get("parameter_name"),
            "required": p.get("required", False),
            "description": (p.get("description") or "")[:150],
        }

        ptype = p.get("type", "")
        if ptype == "QUERY":
            result["query_params"].append(param_info)
        elif ptype == "PATH":
            result["path_params"].append(param_info)
        elif ptype == "BODY":
            mime_types = p.get("mime_types", [])
            if mime_types:
                sample = mime_types[0].get("sample", "")
                param_info["sample"] = sample[:500] if sample else None
            result["body_params"].append(param_info)
        elif ptype == "HEADER":
            result["header_params"].append(param_info)

    return result


def format_endpoint(ep: dict) -> dict:
    """Format a raw endpoint from /help/endpoints into structured info."""
    path = ep.get("path", "")
    http_method = ep.get("http_method", "")
    operation = categorize_endpoint(http_method, path)
    params = parse_parameters(ep.get("parameters", []))

    endpoint_info = {
        "method": http_method,
        "path": path,
        "operation": operation,
        "summary": ep.get("summary", ""),
        "deprecated": ep.get("deprecated", False),
    }

    # Only include non-empty param lists
    for key, value in params.items():
        if value:
            endpoint_info[key] = value

    # Build usage example
    required_query = [p["name"] for p in params["query_params"] if p["required"]]
    required_body = len(params["body_params"]) > 0 and params["body_params"][0].get("required", False)

    usage = f'method="{http_method}", endpoint="{path}"'
    if required_query:
        usage += f', params={{"{required_query[0]}": "..."}}'
    if required_body:
        usage += ', body={...}'

    endpoint_info["usage_example"] = usage

    # Cache for validation
    cache_key = f"{http_method}:{path}"
    _endpoint_cache[cache_key] = endpoint_info

    return endpoint_info


def paths_match(pattern: str, actual: str) -> bool:
    """
    Check if actual path matches a pattern with {param} placeholders.
    e.g., /users/{id} matches /users/123
    """
    pattern_parts = pattern.rstrip("/").split("/")
    actual_parts = actual.rstrip("/").split("/")

    if len(pattern_parts) != len(actual_parts):
        return False

    for p, a in zip(pattern_parts, actual_parts):
        if p.startswith("{") and p.endswith("}"):
            continue  # Path parameter, any value matches
        if p != a:
            return False

    return True


def get_cached_endpoint(method: str, path: str) -> Optional[dict]:
    """Look up a cached endpoint."""
    return _endpoint_cache.get(f"{method}:{path}")
