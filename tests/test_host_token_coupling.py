"""Refuse a host-only override so the operator token stays on the configured host."""

import asyncio
import os
import unittest
from unittest.mock import patch

from src.config import QRadarConfig, hosts_equivalent
from src.client import QRadarClient
from src.tools import HOST_WITHOUT_TOKEN_ERROR, apply_connection_overrides, execute_tool


class HostTokenCouplingTests(unittest.TestCase):
    def test_hosts_equivalent_ignores_scheme_and_slash(self):
        self.assertTrue(hosts_equivalent("https://qradar.lab/", "qradar.lab:443"))
        self.assertFalse(hosts_equivalent("https://qradar.lab", "https://other.lab"))

    def test_explicit_foreign_host_does_not_inherit_env_token(self):
        env = {
            "QRADAR_HOST": "https://operator.lab",
            "QRADAR_API_TOKEN": "OPERATOR_TOKEN",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = QRadarConfig(host="https://caller-chosen.lab")
        self.assertEqual(cfg.host, "https://caller-chosen.lab")
        self.assertEqual(cfg.api_token, "")

    def test_same_host_constructor_may_use_env_token(self):
        env = {
            "QRADAR_HOST": "https://operator.lab",
            "QRADAR_API_TOKEN": "OPERATOR_TOKEN",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = QRadarConfig(host="https://operator.lab/")
        self.assertEqual(cfg.api_token, "OPERATOR_TOKEN")

    def test_host_only_override_is_rejected(self):
        env = {
            "QRADAR_HOST": "https://operator.lab",
            "QRADAR_API_TOKEN": "OPERATOR_TOKEN",
        }
        with patch.dict(os.environ, env, clear=False):
            client = QRadarClient()
            with self.assertRaises(ValueError) as raised:
                apply_connection_overrides(
                    client,
                    {"qradar_host": "https://caller-chosen.lab"},
                )
        self.assertEqual(str(raised.exception), HOST_WITHOUT_TOKEN_ERROR)

    def test_host_and_token_override_uses_caller_token(self):
        env = {
            "QRADAR_HOST": "https://operator.lab",
            "QRADAR_API_TOKEN": "OPERATOR_TOKEN",
        }
        with patch.dict(os.environ, env, clear=False):
            client = QRadarClient()
            overridden = apply_connection_overrides(
                client,
                {
                    "qradar_host": "https://other.lab",
                    "qradar_token": "CALLER_TOKEN",
                },
            )
        self.assertEqual(overridden.host, "https://other.lab")
        self.assertEqual(overridden.api_token, "CALLER_TOKEN")

    def test_execute_tool_rejects_host_only_before_any_request(self):
        env = {
            "QRADAR_HOST": "https://operator.lab",
            "QRADAR_API_TOKEN": "OPERATOR_TOKEN",
        }
        with patch.dict(os.environ, env, clear=False):
            client = QRadarClient()
            result = asyncio.run(
                execute_tool(
                    client,
                    "qradar_get",
                    {
                        "endpoint": "/siem/offenses",
                        "qradar_host": "https://caller-chosen.lab",
                    },
                )
            )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], HOST_WITHOUT_TOKEN_ERROR)


if __name__ == "__main__":
    unittest.main()
