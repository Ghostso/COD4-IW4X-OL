import importlib.util
import io
import os
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "PATCHES" / "work"
sys.dont_write_bytecode = True
sys.path.insert(0, str(WORK))
import codol_crypto as cc
spec = importlib.util.spec_from_file_location("lobby_under_test", WORK / "lobby_server.py")
lobby = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lobby)

PVE_REQUEST = bytes.fromhex("08 01 00 00 00 08 00 00 00 00 08 0a 00 00 00 07 ab ad 92 d6 6b 08 04 00 00 00 01 00 00 00 00 00 00 00 00")
BOT_REQUEST = bytes.fromhex("08 01 00 00 00 08 00 00 00 00 08 32 00 00 00 07 ab ad 92 d6 6b 08 04 00 00 00 01 00 00 00 00 00 00 00 00 10 42 00 00 00 10 74 64 6d 00 10 00 10 4d 37 2d 45 38 53 36 43 6c 69 65 6e 74 00 00")

def fields(data):
    out = []
    i = 0
    sizes = {7: 4, 8: 4, 10: 8, 1: 1}
    while i < len(data):
        tag = data[i]
        i += 1
        if tag in sizes:
            n = sizes[tag]
            out.append((tag, data[i:i + n]))
            i += n
        elif tag == 16:
            end = data.index(0, i)
            out.append((tag, data[i:end].decode("ascii")))
            i = end + 1
        elif tag == 19:
            i += 1
            n = struct.unpack_from("<I", data, i)[0]
            i += 4
            out.append((tag, data[i:i + n]))
            i += n
        else:
            raise AssertionError("unknown tag at %d: %r" % (i - 1, tag))
    return out

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.logs = io.StringIO()
        self.log_patch = patch.object(lobby, "log", lambda message: self.logs.write(message + "\n"))
        self.log_patch.start()
        self.override_patch = patch.object(cc, "_coop_map_override", lambda: "coop_train_mp_firingrange")
        self.override_patch.start()
        self.flag_patch = patch.object(lobby.os.path, "exists", lambda path: path == lobby.FR_SESSION_FLAG)
        self.flag_patch.start()
        lobby.CURRENT_LOBBY_STATE = {"playlist": "unknown", "map": "unknown", "mode": "unknown", "room_id": "-", "request_id": 57}
        lobby.CURRENT_LOBBY_ADDR = "127.0.0.1:60000"
        lobby.get_playlist_resolver().playlists = {}

    def tearDown(self):
        self.flag_patch.stop()
        self.override_patch.stop()
        self.log_patch.stop()

    def test_pve_preserves_map_and_coop_game_type(self):
        objects, _, pushes = lobby.reply_objects(21, 5, PVE_REQUEST)
        values = fields(objects[0])
        self.assertEqual(values[5][1], "coop_train_mp_firingrange")
        self.assertEqual(struct.unpack("<i", values[8][1])[0], 0x1000007)
        self.assertEqual(struct.unpack("<i", values[9][1])[0], 10)
        self.assertEqual(struct.unpack("<i", values[16][1])[0], 1)
        self.assertEqual(len(values[0][1]), 67)
        self.assertEqual(pushes, [])
        text = self.logs.getvalue()
        for event in ("LOBBY_FIND_SESSIONS", "LOBBY_BATTLE_ENDPOINT_ASSIGNED", "LOBBY_MODE_SELECTED"):
            self.assertIn(event, text)
            self.assertIn("playlist=10", text)
            self.assertIn("client=127.0.0.1:60000", text)

    def test_bot_path_is_not_mislabeled_as_pve(self):
        objects, _, _ = lobby.reply_objects(21, 5, BOT_REQUEST)
        values = fields(objects[0])
        self.assertEqual(struct.unpack("<i", values[9][1])[0], 50)
        self.assertNotEqual(struct.unpack("<i", values[8][1])[0], 0x1000003)
        self.assertIn("playlist=50", self.logs.getvalue())
        self.assertNotIn("map=coop_train_mp_firingrange mode=coop", self.logs.getvalue())

    def test_booking_and_start_metadata_without_sensitive_payload(self):
        lobby.reply_objects(21, 5, PVE_REQUEST)
        lobby.reply_objects(6, 14, b"mmbook 1 secret-booking-token 0\x00")
        lobby.reply_objects(6, 14, b"mmstart sv_resetServer; g_gametype coop; map coop_train_mp_firingrange; roomChatChannelID 0;\x00")
        text = self.logs.getvalue()
        for event in ("LOBBY_MMBOOK_RECEIVED", "LOBBY_MMBOOK_RESPONDED", "LOBBY_MMSTART_RECEIVED", "LOBBY_MMSTART_PARSED"):
            self.assertIn(event, text)
        self.assertIn("room_id=0", text)
        self.assertNotIn("secret-booking-token", text)
        self.assertNotIn("LOBBY_HANDOFF_COMPLETE", text)

    def test_room_lifecycle_metadata(self):
        lobby.reply_objects(11, 13, b"")
        self.assertEqual(lobby.CURRENT_LOBBY_STATE["room_id"], "0x1122334455667788")
        lobby.reply_objects(11, 2, b"")
        self.assertEqual(lobby.CURRENT_LOBBY_STATE["room_id"], "-")

if __name__ == "__main__":
    unittest.main()
