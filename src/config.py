"""
QRadar MCP Server Configuration

Centralized environment variable loading with validation.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("qradar-mcp")


def hosts_equivalent(left: str, right: str) -> bool:
    """Compare QRadar hosts without scheme, trailing slash, or default :443."""

    def _norm(value: str) -> str:
        host = (value or "").strip().rstrip("/").lower()
        if host.startswith("https://"):
            host = host[8:]
        elif host.startswith("http://"):
            host = host[7:]
        if host.endswith(":443"):
            host = host[:-4]
        return host

    return bool(left) and bool(right) and _norm(left) == _norm(right)


class QRadarConfig:
    """Load and validate QRadar configuration from environment variables."""

    def __init__(
        self,
        host: Optional[str] = None,
        api_token: Optional[str] = None,
        api_version: str = "20.0",
        verify_ssl: Optional[bool] = None,
        timeout: float = 120.0,
    ):
        env_host = os.environ.get("QRADAR_HOST", "")
        env_token = os.environ.get("QRADAR_API_TOKEN", "")
        explicit_host = host is not None
        explicit_token = api_token is not None

        self.host = (host if explicit_host else env_host).rstrip("/")
        if explicit_token:
            self.api_token = api_token or ""
        elif explicit_host and not hosts_equivalent(self.host, env_host):
            # Do not attach the operator env token to a caller-chosen host.
            self.api_token = ""
        else:
            self.api_token = env_token
        self.api_version = api_version if api_version != "20.0" else os.environ.get("QRADAR_API_VERSION", "20.0")
        self.timeout = timeout

        # SSL verification: Check env var, default to False for self-signed certs
        if verify_ssl is None:
            ssl_env = os.environ.get("QRADAR_VERIFY_SSL", "false").lower()
            self.verify_ssl = ssl_env in ("true", "1", "yes")
        else:
            self.verify_ssl = verify_ssl

        # Validate required credentials
        if not self.host:
            logger.warning("No QRADAR_HOST provided - must be passed in tool arguments")

        if not self.api_token:
            logger.warning("No QRADAR_API_TOKEN provided - must be passed in tool arguments")

        # Log configuration at startup
        if self.host and self.api_token:
            logger.info("QRadar MCP Client initialized")
            logger.info(f"  Host: {self.host}")
            logger.info(f"  SSL Verification: {self.verify_ssl}")
            logger.info(f"  API Version: {self.api_version}")

    @property
    def base_url(self) -> str:
        return f"{self.host}/api" if self.host else ""

    @property
    def headers(self) -> dict:
        return {
            "SEC": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": self.api_version,
        }
