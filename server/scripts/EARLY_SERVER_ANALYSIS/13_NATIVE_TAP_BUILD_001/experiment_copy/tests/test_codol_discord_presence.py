"""Presence must describe the match the client actually entered."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from codol_discord_presence import ClientLog, Match, activity_for, parse_status, verified_match


class PresenceTest(unittest.TestCase):
    def test_match_requires_active_client_and_matching_live_server(self):
        log = ClientLog(Path("unused"))
        log.feed("StartGameRecv")
        log.feed("map:            mp_rust")
        log.feed("type:           dom")
        live = parse_status("sh1x_status map=mp_rust session_map=mp_rust gametype=dom "
                            "type=mp running=1 humans=1 bots=7 maxclients=16 uids=123")
        self.assertIsNone(verified_match(log, live))
        log.feed("CA_PRIMED -> CA_ACTIVE (game views should be displayed)")
        self.assertEqual(verified_match(log, live), live)
        self.assertEqual(activity_for(live, 123).details, "Domination on Rust")
        self.assertEqual(activity_for(live, 123).image, "codol")
        self.assertEqual(activity_for(live, 123).state, "1 player, 7 bots")
        self.assertIsNone(verified_match(log, Match("mp_rust", "combat", 1, 7, 16)))
        self.assertIsNone(verified_match(log, Match("mp_rust", "dom", 0, 8, 16)))
        log.feed("CA_ACTIVE -> CA_DISCONNECTED (not talking to a server)")
        self.assertIsNone(verified_match(log, live))

    def test_new_join_invalidates_previous_match(self):
        log = ClientLog(Path("unused"))
        log.feed("StartGameRecv")
        log.feed("map: mp_nuked")
        log.feed("type: combat")
        log.feed("CA_PRIMED -> CA_ACTIVE")
        log.feed("StartGameRecv")
        self.assertFalse(log.active)
        self.assertEqual(log.map_name, "")

    def test_rejects_stopped_or_inconsistent_server(self):
        self.assertIsNone(parse_status("sh1x_status map=mp_rust session_map=mp_nuked "
                                       "gametype=dom type=mp running=1 humans=1 bots=7 maxclients=16"))
        self.assertIsNone(parse_status("sh1x_status map=mp_rust session_map=mp_rust "
                                       "gametype=dom type=mp running=0 humans=1 bots=7 maxclients=16"))

    def test_official_icon_remains_fixed_across_lobby_and_maps(self):
        self.assertEqual(activity_for(None, 123).image, "codol")
        for map_name in ("mp_killhouse_sh", "mp_rust", "mp_nuked",
                         "zm_prototype_sh", "zm_asylum_sh", "zm_zombie_training",
                         "mp_future_map"):
            with self.subTest(map=map_name):
                activity = activity_for(Match(map_name, "dom", 1, 7, 16), 123)
                self.assertEqual(activity.image, "codol")
                self.assertEqual(activity.image_text, "Call of Duty Online")
                self.assertIn(" on ", activity.details)
                self.assertEqual(activity.state, "1 player, 7 bots")


if __name__ == "__main__":
    unittest.main()
