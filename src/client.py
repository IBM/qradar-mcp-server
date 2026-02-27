"""
QRadar REST API Client

Async HTTP client for QRadar API supporting all HTTP methods.
Uses config.py for configuration and auth.py for authentication.
"""

import logging
from typing import Any, Optional
import httpx

from .config import QRadarConfig
from .auth import QRadarAuth

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
        self.config = QRadarConfig(
            host=host,
            api_token=api_token,
            api_version=api_version,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        self.auth = QRadarAuth(
            api_token=self.config.api_token,
            api_version=self.config.api_version,
        )

        # Expose for backward compatibility
        self.host = self.config.host
        self.api_token = self.config.api_token
        self.verify_ssl = self.config.verify_ssl
        self.timeout = self.config.timeout
        self.base_url = self.config.base_url
        self.headers = self.config.headers

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
