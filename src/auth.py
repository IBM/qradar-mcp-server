"""
QRadar Authentication

Token management for QRadar REST API.
QRadar uses a static SEC token (no OAuth2 refresh needed).
This module validates and provides the auth header.
"""

import logging
from typing import Optional

logger = logging.getLogger("qradar-mcp")


class QRadarAuth:
    """Manage QRadar API authentication via SEC token."""

    def __init__(self, api_token: str, api_version: str = "26.0"):
        self.api_token = api_token
        self.api_version = api_version

    def get_headers(self) -> dict:
        """Return authentication headers for QRadar API requests."""
        return {
            "SEC": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": self.api_version,
        }

    @property
    def is_configured(self) -> bool:
        """Check if authentication token is available."""
        return bool(self.api_token)
