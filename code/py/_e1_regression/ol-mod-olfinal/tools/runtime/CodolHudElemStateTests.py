#!/usr/bin/env python3
"""Offline contract tests for the read-only CODOL HudElem probe."""

from __future__ import annotations

import unittest

import CodolHudElemState


class CodolHudElemStateTests(unittest.TestCase):
    def test_snapshot_layout_matches_recovered_codol_contract(self) -> None:
        self.assertEqual(CodolHudElemState.HUDELEM_SIZE, 0xA8)
        self.assertEqual(CodolHudElemState.HUDELEM_COUNT, 31)
        self.assertEqual(CodolHudElemState.HUDELEM_FIELD_COUNT, 42)
        self.assertEqual(CodolHudElemState.HUDELEM_CURRENT_OFFSET, 0xA78)
        self.assertEqual(CodolHudElemState.HUDELEM_ARCHIVAL_OFFSET, 0x1ED0)

    def test_probe_is_read_only_and_reports_descriptor_metadata(self) -> None:
        script = CodolHudElemState.build_script()
        self.assertIn("function readDescriptor(index)", script)
        self.assertIn("current: readArray", script)
        self.assertIn("archival: readArray", script)
        self.assertIn("change_hint", script)
        self.assertNotIn("writeU8", script)
        self.assertNotIn("writeU32", script)
        self.assertNotIn("writeFloat", script)


if __name__ == "__main__":
    unittest.main()
