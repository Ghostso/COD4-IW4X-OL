#!/usr/bin/env python3
"""Regression tests for the CODOL script builtin matrix generator."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from CodolBuiltinMatrix import (
    PE32Image,
    TableSpec,
    analyze_iw4_usage,
    extract_table,
    find_exact_c_strings,
    strip_gsc_non_code,
)


def make_test_pe(path: Path) -> None:
    data = bytearray(0x800)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    file_header = 0x84
    struct.pack_into("<H", data, file_header, 0x14C)
    struct.pack_into("<H", data, file_header + 2, 2)
    struct.pack_into("<H", data, file_header + 16, 0xE0)
    optional = file_header + 20
    struct.pack_into("<H", data, optional, 0x10B)
    struct.pack_into("<I", data, optional + 28, 0x400000)
    struct.pack_into("<I", data, optional + 60, 0x200)
    section_table = optional + 0xE0
    data[section_table : section_table + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", data, section_table + 8, 0x200, 0x1000, 0x200, 0x200)
    struct.pack_into("<I", data, section_table + 36, 0x60000020)
    second = section_table + 40
    data[second : second + 8] = b".rdata\0\0"
    struct.pack_into("<IIII", data, second + 8, 0x400, 0x2000, 0x400, 0x400)
    struct.pack_into("<I", data, second + 36, 0x40000040)
    struct.pack_into("<III", data, 0x400, 0x402100, 0x401020, 7)
    data[0x500:0x50B] = b"giveweapon\0"
    path.write_bytes(data)


class BuiltinMatrixTests(unittest.TestCase):
    def test_pe_mapping_and_table_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.exe"
            make_test_pe(path)
            image = PE32Image(path)
            rows = extract_table(
                image,
                TableSpec("test", "server", "function", "generic", 0x402000, 1, 12, True),
            )
        self.assertEqual(image.image_base, 0x400000)
        self.assertEqual(image.va_to_offset(0x402100), 0x500)
        self.assertEqual(rows[0]["name"], "giveweapon")
        self.assertEqual(rows[0]["handler_va"], "0x00401020")
        self.assertEqual(rows[0]["type"], 7)

    def test_non_code_stripping_preserves_lines_and_ignores_names(self) -> None:
        source = 'giveweapon(); // takeweapon()\n/# setperk() #/\n"setorigin()"\n'
        code = strip_gsc_non_code(source)
        self.assertIn("giveweapon()", code)
        self.assertNotIn("takeweapon", code)
        self.assertNotIn("setperk", code)
        self.assertNotIn("setorigin", code)
        self.assertEqual(code.count("\n"), source.count("\n"))

    def test_iw4_usage_excludes_definition_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "one.gsc").write_text(
                "helper() { self giveweapon(\"x\"); }\n"
                "giveweapon() { }\n"
                "// self takeweapon(\"x\");\n",
                encoding="utf-8",
            )
            (root / "two.gsc").write_text(
                "main() { player GiveWeapon(\"y\"); player takeweapon(\"y\"); }\n",
                encoding="utf-8",
            )
            usage = analyze_iw4_usage(root, {"giveweapon", "takeweapon"})
        self.assertEqual(usage["giveweapon"]["call_count"], 2)
        self.assertEqual(usage["giveweapon"]["file_count"], 2)
        self.assertEqual(usage["takeweapon"]["call_count"], 1)

    def test_invalid_handler_section_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.exe"
            make_test_pe(path)
            data = bytearray(path.read_bytes())
            struct.pack_into("<I", data, 0x404, 0x402100)
            path.write_bytes(data)
            image = PE32Image(path)
            with self.assertRaisesRegex(ValueError, "not executable"):
                extract_table(
                    image,
                    TableSpec("test", "server", "function", "generic", 0x402000, 1, 12, True),
                )

    def test_exact_c_string_scan_rejects_identifier_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.exe"
            make_test_pe(path)
            data = bytearray(path.read_bytes())
            data[0x520:0x536] = b"prefixgiveweapon\0\0spawn\0"
            path.write_bytes(data)
            occurrences = find_exact_c_strings(PE32Image(path), {"giveweapon", "spawn"})
        self.assertEqual(len(occurrences["giveweapon"]), 1)
        self.assertEqual(len(occurrences["spawn"]), 1)


if __name__ == "__main__":
    unittest.main()
