#!/usr/bin/env python3
"""Regression tests for CODOL XAsset manifest comparison."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from CodolXAssetManifestDiff import diff_manifests


class XAssetManifestDiffTests(unittest.TestCase):
    def test_diff_ignores_runtime_addresses_and_indices(self) -> None:
        before = {
            "assets": [
                {"name": "maps/test.gsc", "length": 4, "header": "0x1000", "index": 1}
            ]
        }
        after = {
            "assets": [
                {"name": "MAPS/TEST.GSC", "length": 4, "header": "0x9000", "index": 8}
            ]
        }
        result = diff_manifests(before, after)
        self.assertEqual(result["changed_count"], 0)
        self.assertEqual(result["unchanged_count"], 1)
        self.assertEqual(result["added_count"], 0)
        self.assertEqual(result["removed_count"], 0)

    def test_diff_classifies_added_removed_and_changed_assets(self) -> None:
        before = {
            "assets": [
                {"name": "same.bin", "length": 4},
                {"name": "changed.bin", "length": 4},
                {"name": "removed.bin", "length": 1},
            ]
        }
        after = {
            "assets": [
                {"name": "same.bin", "length": 4},
                {"name": "changed.bin", "length": 5},
                {"name": "added.bin", "length": 1},
            ]
        }
        result = diff_manifests(before, after)
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["removed_count"], 1)
        self.assertEqual(result["changed_count"], 1)
        self.assertEqual(result["unchanged_count"], 1)

    def test_diff_hashes_dumped_payload_when_manifest_has_no_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before_dir = root / "before"
            after_dir = root / "after"
            before_dir.mkdir()
            after_dir.mkdir()
            (before_dir / "asset.bin").write_bytes(b"one")
            (after_dir / "asset.bin").write_bytes(b"two")
            before = {"assets": [{"name": "asset.bin", "length": 3, "output": "asset.bin"}]}
            after = {"assets": [{"name": "asset.bin", "length": 3, "output": "asset.bin"}]}
            result = diff_manifests(before, after, before_dir, after_dir)
            self.assertEqual(result["changed_count"], 1)
            self.assertIn("sha256", result["changed"][0]["before"][0])


if __name__ == "__main__":
    unittest.main()
