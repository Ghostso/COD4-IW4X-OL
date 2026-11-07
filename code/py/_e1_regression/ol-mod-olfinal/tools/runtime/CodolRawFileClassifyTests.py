#!/usr/bin/env python3
"""Regression tests for content-based CODOL RawFile classification."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from CodolRawFileClassify import COMPILED_GSC_MAGIC, classify_manifest, classify_payload


class RawFileClassifyTests(unittest.TestCase):
    def test_empty_payload(self) -> None:
        result = classify_payload(b"")
        self.assertEqual(result["classification"], "empty")

    def test_compiled_gsc_magic_precedes_text_detection(self) -> None:
        result = classify_payload(COMPILED_GSC_MAGIC + b"\x36payload")
        self.assertEqual(result["classification"], "known_compiled_gsc_magic")
        self.assertEqual(result["compiled_gsc_version"], 0x36)

    def test_gsc_source_is_recognized_without_extension(self) -> None:
        result = classify_payload(
            b'main()\n{\n  level._effect["fire"] = loadfx("fire/test");\n}\n'
        )
        self.assertEqual(result["classification"], "gsc_source")
        self.assertEqual(result["script_candidate_confidence"], "high")

    def test_animation_dsl_is_distinct_from_gsc(self) -> None:
        result = classify_payload(
            b"Character Animation Script\n\nDEFINES\nset movetype moving = walk AND run\n"
        )
        self.assertEqual(result["classification"], "engine_script_text")

    def test_plain_config_remains_other_text(self) -> None:
        result = classify_payload(b"seta r_fullscreen 1\nseta com_maxfps 85\n")
        self.assertEqual(result["classification"], "other_text")

    def test_known_and_unknown_binary_are_distinguished(self) -> None:
        known = classify_payload(b"DDS " + bytes(range(32)))
        unknown = classify_payload(b"\x00\xff\x81\x02\x00\xf0")
        self.assertEqual(known["classification"], "binary")
        self.assertEqual(known["known_magic"], "dds")
        self.assertEqual(known["script_candidate_confidence"], "unlikely")
        self.assertEqual(unknown["classification"], "binary")
        self.assertIsNone(unknown["known_magic"])
        self.assertEqual(unknown["script_candidate_confidence"], "unknown")

    def test_codols_seen_binary_magics_are_not_unknown_candidates(self) -> None:
        baseline = classify_payload(b"IWCB000" + b"\x01\x00\x00\x00")
        scaleform = classify_payload(b"GFX\x0a" + b"\xff\x00\x80")
        self.assertEqual(baseline["known_magic"], "codol-const-baseline")
        self.assertEqual(scaleform["known_magic"], "scaleform-gfx")
        self.assertEqual(baseline["script_candidate_confidence"], "unlikely")
        self.assertEqual(scaleform["script_candidate_confidence"], "unlikely")

    def test_manifest_classification_uses_dumped_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = root / "files"
            files.mkdir()
            (files / "renamed_asset").write_bytes(b"main()\n{\n self notify(\"ready\");\n}\n")
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "name": "renamed_asset",
                                "output": "files/renamed_asset",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = classify_manifest(root / "manifest.json")
        self.assertEqual(report["asset_count"], 1)
        self.assertEqual(report["classification_counts"], {"gsc_source": 1})


if __name__ == "__main__":
    unittest.main()
