#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import CodolClientAccount


class CodolClientAccountTests(unittest.TestCase):
    def test_seed_copies_player_state_under_an_independent_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "1100001DEADC0DE"
            source.mkdir()
            for index, name in enumerate(CodolClientAccount.COPIED_PLAYER_FILES):
                (source / name).write_bytes(f"state-{index}".encode())

            target = CodolClientAccount.seed_account(
                root,
                "01100001DEADC0DE",
                "DEADC0DF",
                "olmod-player2",
            )

            self.assertEqual(target.name, "1100001DEADC0DF")
            for name in CodolClientAccount.COPIED_PLAYER_FILES:
                self.assertEqual((target / name).read_bytes(), (source / name).read_bytes())
            self.assertEqual(
                json.loads((target / "Identity.json").read_text(encoding="utf-8")),
                {"schemaVersion": 1, "displayName": "olmod-player2"},
            )

    def test_existing_target_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "1100001DEADC0DE"
            target = root / "1100001DEADC0DF"
            source.mkdir()
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("preserve", encoding="ascii")
            with self.assertRaises(FileExistsError):
                CodolClientAccount.seed_account(
                    root,
                    "01100001DEADC0DE",
                    "01100001DEADC0DF",
                    "player2",
                )
            self.assertEqual(marker.read_text(encoding="ascii"), "preserve")

    def test_invalid_identity_is_rejected(self) -> None:
        self.assertEqual(
            CodolClientAccount.normalize_user_id("DEADC0DF"),
            "01100001DEADC0DF",
        )
        self.assertEqual(
            CodolClientAccount.user_id_directory("01100001DEADC0DF"),
            "1100001DEADC0DF",
        )
        with self.assertRaises(ValueError):
            CodolClientAccount.validate_display_name("\N{SNOWMAN}")

    def test_main_prints_padded_platform_id_not_directory_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "1100001DEADC0DE"
            source.mkdir()
            for name in CodolClientAccount.COPIED_PLAYER_FILES:
                (source / name).write_bytes(b"state")
            output = StringIO()
            argv = [
                "CodolClientAccount.py",
                "--player-root", str(root),
                "--source-user-id", "01100001DEADC0DE",
                "--target-user-id", "01100001DEADC0DF",
                "--display-name", "olmod-player2",
            ]
            with mock.patch("sys.argv", argv), redirect_stdout(output):
                self.assertEqual(CodolClientAccount.main(), 0)

            self.assertIn("1100001DEADC0DF", output.getvalue())
            self.assertIn(
                "OLMOD_PLATFORM_USER_ID=01100001DEADC0DF",
                output.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
