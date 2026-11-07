#!/usr/bin/env python3
"""Regression tests for the idalib-mcp command-line client."""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

import IdalibMcpClient


class IdalibMcpClientTests(unittest.TestCase):
    def test_stdin_json_is_forwarded_as_tool_arguments(self) -> None:
        requests: list[tuple[dict, str | None]] = []

        def fake_post(
            _url: str, payload: dict, session_id: str | None = None
        ) -> tuple[str | None, str]:
            requests.append((payload, session_id))
            if payload["method"] == "initialize":
                return "test-session", "{}"
            if payload["method"] == "tools/call":
                return session_id, json.dumps({"result": {"structuredContent": {"ok": True}}})
            return session_id, "{}"

        stdin = io.StringIO('{"database":"codol-mainline-pmove","addr":"0x004522B0"}')
        stdout = io.StringIO()
        with (
            patch.object(IdalibMcpClient, "post", side_effect=fake_post),
            patch("sys.argv", ["IdalibMcpClient.py", "decompile", "-"]),
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
        ):
            result = IdalibMcpClient.main()

        self.assertEqual(result, 0)
        self.assertEqual(requests[1][0]["method"], "notifications/initialized")
        self.assertEqual(requests[1][1], "test-session")
        self.assertEqual(requests[2][0]["params"]["name"], "decompile")
        self.assertEqual(
            requests[2][0]["params"]["arguments"],
            {"database": "codol-mainline-pmove", "addr": "0x004522B0"},
        )
        self.assertEqual(json.loads(stdout.getvalue()), {"ok": True})

    def test_stdin_accepts_powershell_utf8_bom(self) -> None:
        def fake_post(
            _url: str, payload: dict, session_id: str | None = None
        ) -> tuple[str | None, str]:
            if payload["method"] == "initialize":
                return "test-session", "{}"
            if payload["method"] == "tools/call":
                return session_id, json.dumps(
                    {"result": {"structuredContent": payload["params"]["arguments"]}}
                )
            return session_id, "{}"

        stdin = io.TextIOWrapper(
            io.BytesIO(b'\xef\xbb\xbf{"database":"codol-pmove-adapter"}'),
            encoding="cp936",
        )
        stdout = io.StringIO()
        with (
            patch.object(IdalibMcpClient, "post", side_effect=fake_post),
            patch("sys.argv", ["IdalibMcpClient.py", "server_health", "-"]),
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
        ):
            result = IdalibMcpClient.main()

        self.assertEqual(result, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"database": "codol-pmove-adapter"},
        )

    def test_batch_reuses_session_and_preserves_result_order(self) -> None:
        requests: list[tuple[dict, str | None]] = []

        def fake_post(
            _url: str, payload: dict, session_id: str | None = None
        ) -> tuple[str | None, str]:
            requests.append((payload, session_id))
            if payload["method"] == "initialize":
                return "test-session", "{}"
            if payload["method"] == "tools/call":
                addr = payload["params"]["arguments"]["addr"]
                return session_id, json.dumps(
                    {"result": {"structuredContent": {"addr": addr}}}
                )
            return session_id, "{}"

        stdin = io.StringIO('[{"addr":"0x417460"},{"addr":"0x424c20"}]')
        stdout = io.StringIO()
        with (
            patch.object(IdalibMcpClient, "post", side_effect=fake_post),
            patch(
                "sys.argv",
                ["IdalibMcpClient.py", "decompile", "-", "--batch"],
            ),
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
        ):
            result = IdalibMcpClient.main()

        self.assertEqual(result, 0)
        self.assertEqual(len(requests), 4)
        self.assertTrue(all(session == "test-session" for _, session in requests[1:]))
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "results": [
                    {"ok": True, "index": 0, "result": {"addr": "0x417460"}},
                    {"ok": True, "index": 1, "result": {"addr": "0x424c20"}},
                ]
            },
        )


if __name__ == "__main__":
    unittest.main()
