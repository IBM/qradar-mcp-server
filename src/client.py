"""
QRadar REST API Client

Async HTTP client for QRadar API supporting all HTTP methods.
"""

import os
import sys
import logging
from typing import Any, Optional
import httpx

logger = logging.getLogger("qradar-mcp")


class QRadarClient:
    """Async HTTP client for QRadar REST API."""

    def __init__(
        self,
        host: Optional[str] = None,
        api_token: Optional[str] = None,
        api_version: str = "26.0",
        verify_ssl: Optional[bool] = None,
        timeout: float = 120.0,
    ):
        # Priority: Constructor args > Environment variables
        self.host = (host or os.environ.get("QRADAR_HOST", "")).rstrip("/")
        self.api_token = api_token or os.environ.get("QRADAR_API_TOKEN", "")
        self.api_version = api_version
        
        # SSL verification: Check env var, default to False for self-signed certs
        if verify_ssl is None:
            ssl_env = os.environ.get("QRADAR_VERIFY_SSL", "false").lower()
            self.verify_ssl = ssl_env in ("true", "1", "yes")
        else:
            self.verify_ssl = verify_ssl
            
        self.timeout = timeout

        # Validate required credentials
        # Don't exit - just warn. Credentials can be passed in tool arguments.
        if not self.host:
            logger.warning("No QRADAR_HOST provided - must be passed in tool arguments")
            
        if not self.api_token:
            logger.warning("No QRADAR_API_TOKEN provided - must be passed in tool arguments")
        
        # Log configuration at startup
        if self.host and self.api_token:
            logger.info(f"QRadar MCP Client initialized")
            logger.info(f"  Host: {self.host}")
            logger.info(f"  SSL Verification: {self.verify_ssl}")
            logger.info(f"  API Version: {self.api_version}")

        self.base_url = f"{self.host}/api" if self.host else ""
        self.headers = {
            "SEC": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": self.api_version,
        }

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
        range_header: Optional[str] = None,
    ) -> dict[str, Any]:
        """Make HTTP request to QRadar API."""
        
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()
        
        if range_header:
            headers["Range"] = f"items={range_header}"

        async with httpx.AsyncClient(
            verify=self.verify_ssl,
            timeout=self.timeout,
            headers=headers,
        ) as client:
            try:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=body,
                )

                if response.status_code == 204:
                    return {"success": True, "data": None, "status_code": 204}

                try:
                    data = response.json()
                except Exception:
                    data = response.text

                if response.status_code >= 400:
                    return {
                        "success": False,
                        "error": self._format_error(response.status_code, data),
                        "status_code": response.status_code,
                        "detail": data,
                    }

                return {
                    "success": True,
                    "data": data,
                    "status_code": response.status_code,
                }

            except httpx.ConnectError as e:
                return {"success": False, "error": f"Connection failed: {self.host}", "detail": str(e)}
            except httpx.TimeoutException as e:
                return {"success": False, "error": "Request timed out", "detail": str(e)}
            except Exception as e:
                return {"success": False, "error": "Unexpected error", "detail": str(e)}

    def _format_error(self, status_code: int, data: Any) -> str:
        messages = {
            400: "Bad request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not found",
            409: "Conflict",
            422: "Invalid parameter",
            429: "Rate limited",
            500: "Server error",
        }
        base = messages.get(status_code, f"HTTP {status_code}")
        if isinstance(data, dict) and "message" in data:
            return f"{base}: {data['message']}"
        return base
