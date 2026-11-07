#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from CodolNetfieldDump import (
    PLAYERSTATE_FIELD_COUNT,
    PLAYERSTATE_TABLE_RVA,
    parse_int,
    sha256_file,
    validate_entries,
)


class CodolNetfieldDumpTests(unittest.TestCase):
    def test_parse_int_accepts_hex_and_decimal(self) -> None:
        self.assertEqual(parse_int("0x855f70"), PLAYERSTATE_TABLE_RVA)
        self.assertEqual(parse_int("84"), 84)
        self.assertEqual(PLAYERSTATE_FIELD_COUNT, 235)

    def test_sha256_file_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.bin"
            path.write_bytes(b"CODOL")
            self.assertEqual(
                sha256_file(path),
                "658C80BEB6AB0216A3085029EEAACBB8C4E4DB3CED47FCCAAD1217416441A407",
            )

    def test_validate_entries_accepts_recovered_layout(self) -> None:
        validate_entries(
            [
                {"index": 0, "offset": 0, "bits": -97, "change_hint": 0},
                {"index": 1, "offset": 536, "bits": -101, "change_hint": 2},
            ],
            2,
        )
        validate_entries(
            [{"index": 0, "offset": 24, "bits": -83, "change_hint": 6}],
            1,
            maximum_change_hint=8,
        )

    def test_validate_entries_rejects_wrong_index_or_hint(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "index mismatch"):
            validate_entries(
                [{"index": 1, "offset": 0, "bits": 8, "change_hint": 0}], 1
            )
        with self.assertRaisesRegex(RuntimeError, "change hint"):
            validate_entries(
                [{"index": 0, "offset": 0, "bits": 8, "change_hint": 4}], 1
            )


if __name__ == "__main__":
    unittest.main()
