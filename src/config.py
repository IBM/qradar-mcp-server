"""
QRadar MCP Server Configuration

Centralized environment variable loading with validation.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("qradar-mcp")


class QRadarConfig:
    """Load and validate QRadar configuration from environment variables."""

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
