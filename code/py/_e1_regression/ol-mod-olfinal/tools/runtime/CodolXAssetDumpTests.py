#!/usr/bin/env python3
"""Regression tests for the CODOL RawFile inventory and dump tool."""

from __future__ import annotations

import hashlib
import unittest

from CodolXAssetDump import AGENT_SOURCE, asset_selected, safe_asset_path


class XAssetDumpTests(unittest.TestCase):
    def test_agent_uses_native_db_entrypoints(self) -> None:
        self.assertIn("module.base.add(0x9ED90)", AGENT_SOURCE)
        self.assertIn("module.base.add(0x9E7D0)", AGENT_SOURCE)
        self.assertIn("module.base.add(0xA1620)", AGENT_SOURCE)
        self.assertIn("mov edi, [esp+4]", AGENT_SOURCE)
        self.assertIn("mov ecx, [esp+4]", AGENT_SOURCE)
        self.assertNotIn("0x1BC9F20", AGENT_SOURCE)
        self.assertNotIn("0x1FC4E28", AGENT_SOURCE)

    def test_default_style_patterns_are_case_insensitive(self) -> None:
        patterns = ("*.gsc", "*.cas")
        self.assertTrue(asset_selected("maps/mp/gametypes/_globallogic.GSC", patterns, False))
        self.assertTrue(asset_selected("clientscripts/example.cas", patterns, False))
        self.assertFalse(asset_selected("mp/table.csv", patterns, False))
        self.assertTrue(asset_selected("mp/table.csv", patterns, True))

    def test_safe_asset_path_preserves_asset_directories(self) -> None:
        self.assertEqual(
            safe_asset_path(r"maps\mp\gametypes\sd.gsc", "fallback.bin").as_posix(),
            "maps/mp/gametypes/sd.gsc",
        )

    def test_safe_asset_path_cannot_escape_output(self) -> None:
        result = safe_asset_path(r"..\..\C:\bad:name?.gsc", "fallback.bin")
        self.assertNotIn("..", result.parts)
        self.assertNotIn(":", str(result))
        self.assertNotIn("?", str(result))

    def test_safe_asset_path_handles_empty_and_reserved_names(self) -> None:
        self.assertEqual(safe_asset_path("", "fallback.bin").as_posix(), "fallback.bin")
        self.assertEqual(safe_asset_path("CON.gsc", "fallback.bin").as_posix(), "_CON.gsc")

    def test_payload_hash_format_matches_manifest_contract(self) -> None:
        self.assertEqual(
            hashlib.sha256(b"test").hexdigest().upper(),
            "9F86D081884C7D659A2FEAA0C55AD015A3BF4F1B2B0B822CD15D6C15B0F00A08",
        )


if __name__ == "__main__":
    unittest.main()
