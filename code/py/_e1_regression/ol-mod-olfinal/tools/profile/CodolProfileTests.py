#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
import struct
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from CodolProfile import (
    RANK_VERSION,
    PUBLIC_DDL_CHECKSUM,
    PUBLIC_DDL_VERSION,
    SECURE_DDL_CHECKSUM,
    SECURE_DDL_VERSION,
    VALIDATED_FIELDS,
    PublicProfile,
    SecureProfile,
    apply_editor_document,
    apply_document,
    profile_document,
    public_profile_path,
    write_profile,
)
from CodolInventory import write_inventory


class SecureProfileTests(unittest.TestCase):
    def test_default_profile_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Privateprofile"
            write_profile(path, SecureProfile.create())
            loaded = SecureProfile.load(path)
            self.assertEqual(loaded.progression()["level"], 1)
            self.assertEqual(loaded.get("rankVersion"), RANK_VERSION)
            self.assertEqual(int.from_bytes(loaded.data[4:8], "little"), SECURE_DDL_VERSION)
            self.assertEqual(int.from_bytes(loaded.data[8:12], "little"), SECURE_DDL_CHECKSUM)
            self.assertEqual(len(VALIDATED_FIELDS), 36)

    def test_progression_uses_native_rank_thresholds(self) -> None:
        profile = SecureProfile.create()
        start, target = profile.xp_range(30, 1)
        self.assertEqual((start, target), (528625, 572187))
        profile.set_progression(level=30, prestige=1, experience=start + 10)
        self.assertEqual(profile.progression()["level"], 30)
        self.assertEqual(profile.progression()["prestige"], 1)
        self.assertEqual(profile.get("experience"), start + 10)

    def test_validated_values_survive_trailing_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Privateprofile"
            profile = SecureProfile.create()
            profile.set("kills", 125.0)
            profile.set("deaths", 25)
            write_profile(path, profile)
            loaded = SecureProfile.load(path)
            self.assertEqual(loaded.get("kills"), 125.0)
            self.assertEqual(loaded.get("deaths"), 25)

    def test_rejects_inconsistent_experience(self) -> None:
        profile = SecureProfile.create()
        with self.assertRaises(ValueError):
            profile.set_progression(level=10, prestige=0, experience=0)

    def test_api_document_creates_native_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Privateprofile"
            document = {
                "progression": {"level": 30, "prestige": 1, "experience": 528625},
                "fields": {"kills": 125, "deaths": 25, "score": 10000},
            }
            with patch("CodolProfile.is_game_running", return_value=False):
                result = apply_document(path, 0x1100001DEADC0DE, document)
                reloaded = profile_document(path, 0x1100001DEADC0DE)

            self.assertTrue(result["exists"])
            self.assertEqual(result["ddlChecksum"], "0x8A317D69")
            self.assertEqual(reloaded["progression"]["level"], 30)
            self.assertEqual(reloaded["fields"]["kills"], 125.0)
            self.assertEqual(len(reloaded["rankTable"]), 70)

    def test_public_identity_round_trip_updates_validation_trailer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Publicprofile"
            data = bytearray(0x8000)
            struct.pack_into("<I", data, 4, PUBLIC_DDL_VERSION)
            struct.pack_into("<I", data, 8, PUBLIC_DDL_CHECKSUM)
            trailing = (bytes([0x07]) + bytes(4)) * 125 + bytes(1)
            profile = PublicProfile(
                data, trailing, compressed=True, optional_user_id=None
            )
            profile.set("badge", 40001)
            profile.set("cardIcon", 30564)
            profile.set("currentCharacterIndex", 3)
            write_profile(path, profile)

            loaded = PublicProfile.load(path)
            self.assertEqual(loaded.get("badge"), 40001)
            self.assertEqual(loaded.get("cardIcon"), 30564)
            self.assertEqual(loaded.get("currentCharacterIndex"), 3)
            self.assertEqual(struct.unpack_from("<i", loaded.trailing, 1)[0], 40001)
            self.assertEqual(struct.unpack_from("<i", loaded.trailing, 11)[0], 30564)

    def test_public_path_is_sibling_of_private_profile(self) -> None:
        path = Path("owner") / "Privateprofile"
        self.assertEqual(public_profile_path(path), Path("owner") / "Publicprofile")

    def test_editor_saves_and_synchronizes_all_sections_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_path = Path(directory) / "Privateprofile"
            write_profile(private_path, SecureProfile.create())
            data = bytearray(0x8000)
            struct.pack_into("<I", data, 4, PUBLIC_DDL_VERSION)
            struct.pack_into("<I", data, 8, PUBLIC_DDL_CHECKSUM)
            trailing = (bytes([0x07]) + bytes(4)) * 125 + bytes(1)
            write_profile(
                public_profile_path(private_path),
                PublicProfile(data, trailing, compressed=True, optional_user_id=None),
            )
            write_inventory(private_path.with_name("Inventory.json"), {"items": []})
            document = {
                "private": {
                    "progression": {"level": 11, "prestige": 0, "experience": 37400},
                    "fields": {"kills": 25},
                },
                "public": {"badge": 40001, "currentCharacterIndex": 2},
                "inventory": {"items": [{"id": 40001, "quantity": 1}]},
            }
            calls: list[list[str]] = []

            def fake_sync(targets: list[str]) -> list[SimpleNamespace]:
                calls.append(targets)
                return [
                    SimpleNamespace(target=target, generation=1, state="succeeded", error_code=0)
                    for target in targets
                ]

            with patch("CodolProfile.is_game_running", return_value=True), patch(
                "CodolProfile.synchronize", side_effect=fake_sync
            ):
                result = apply_editor_document(private_path, 0x1100001DEADC0DE, document)

            self.assertEqual(calls, [["inventory", "public", "private"]])
            self.assertEqual(result["private"]["progression"]["level"], 11)
            self.assertEqual(result["public"]["fields"]["badge"], 40001)
            self.assertEqual(result["inventory"]["items"][0]["id"], 40001)


if __name__ == "__main__":
    unittest.main()
