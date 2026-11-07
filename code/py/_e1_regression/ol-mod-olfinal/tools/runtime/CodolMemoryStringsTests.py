#!/usr/bin/env python3
"""Regression tests for the bounded CODOL memory string scanner."""

from __future__ import annotations

import argparse
import unittest

from CodolMemoryStrings import AGENT_SOURCE, address_value, clip_ranges


class MemoryStringsTests(unittest.TestCase):
    def test_agent_enumerates_readable_ranges_once(self) -> None:
        self.assertEqual(AGENT_SOURCE.count("Process.enumerateRanges"), 1)
        self.assertIn("protection: 'r--'", AGENT_SOURCE)

    def test_address_value_accepts_decimal_and_hex(self) -> None:
        self.assertEqual(address_value("4096"), 0x1000)
        self.assertEqual(address_value("0x1cdb0000"), 0x1CDB0000)

    def test_address_value_rejects_negative_or_invalid_values(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            address_value("-1")
        with self.assertRaises(argparse.ArgumentTypeError):
            address_value("not-an-address")

    def test_clip_ranges_returns_only_readable_intersections(self) -> None:
        ranges = [
            {
                "base": "0x1000",
                "size": 0x1000,
                "protection": "r--",
                "file": {"path": "image.exe", "offset": 0x200, "size": 0x1000},
            },
            {"base": "0x3000", "size": 0x1000, "protection": "rw-", "file": None},
        ]

        clipped = clip_ranges(ranges, 0x1800, 0x2000)

        self.assertEqual(
            [(entry["base"], entry["size"]) for entry in clipped],
            [("0x1800", 0x800), ("0x3000", 0x800)],
        )
        self.assertEqual(clipped[0]["file"]["offset"], 0xA00)
        self.assertEqual(clipped[0]["file"]["size"], 0x800)
        self.assertEqual(clipped[0]["source_base"], "0x1000")

    def test_clip_ranges_preserves_unfiltered_input(self) -> None:
        ranges = [{"base": "0x1000", "size": 0x100, "file": None}]
        self.assertIs(clip_ranges(ranges, None, None), ranges)

    def test_clip_ranges_requires_both_bounds(self) -> None:
        with self.assertRaises(ValueError):
            clip_ranges([], 0x1000, None)


if __name__ == "__main__":
    unittest.main()
