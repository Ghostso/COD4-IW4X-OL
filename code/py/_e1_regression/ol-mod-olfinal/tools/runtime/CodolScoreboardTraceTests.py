#!/usr/bin/env python3

from __future__ import annotations

import unittest

import CodolScoreboardTrace


class CodolScoreboardTraceTests(unittest.TestCase):
    def test_script_observes_command_mirror_and_ui_boundaries(self) -> None:
        script = CodolScoreboardTrace.build_script()
        self.assertIn("observe('server_command'", script)
        self.assertIn("observe('update_score'", script)
        self.assertIn("observe('copy_scoreboard_to_ui'", script)
        self.assertIn("observe('populate_scoreboard_ui'", script)
        self.assertIn("observe('score_view_update_score'", script)
        self.assertIn("observe('score_view_initialize'", script)
        self.assertIn("observe('score_view_update'", script)
        self.assertIn("observe('view_manager_update'", script)
        self.assertIn("observe('ingame_gfx_initialize'", script)
        self.assertIn("observe('register_common_as_functions'", script)
        self.assertIn("observe('register_score_view_as_function'", script)
        self.assertIn("observe('register_sandd_view_as_function'", script)
        self.assertIn("observe('sandd_view_initialize'", script)
        self.assertIn("CG_SANDD_VIEW_BUILD_STATE_RVA", CodolScoreboardTrace.__dict__)
        self.assertIn("sandd_view_build_state", script)
        self.assertIn("ui_enable_hudkit: readDvar('ui_enable_hudkit')", script)
        self.assertIn("ui_gametype: readDvar('ui_gametype')", script)
        self.assertIn("client_sources: readScoreboardClientSources(cgame)", script)
        self.assertIn("team: readS32(source.add(8))", script)
        self.assertIn("CG_SCORE_VIEW_TIMER_SUBTRACT_RVA", CodolScoreboardTrace.__dict__)
        self.assertIn("clientTime - snapshotTime", script)
        self.assertIn("playlist: readPlaylistSlot(26)", script)
        self.assertIn("raw_index: rawIndex", script)
        self.assertIn("words_near_present: words", script)
        self.assertIn("playlist_catalog: readPlaylistCatalog()", script)
        self.assertIn("playlist_raw: readPlaylistRaw(133)", script)
        self.assertIn("playlist_rule_filters:", script)
        self.assertIn("systeminfo_configstring: readUtf8(clGetConfigString(1))", script)
        self.assertIn("target_configstring_dvar_pairs: readTargetConfigStringDvarPairs()", script)
        self.assertIn("value_index: valueIndex", script)
        self.assertNotIn("writeU32", script)

    def test_script_uses_requested_playlist_slot(self) -> None:
        script = CodolScoreboardTrace.build_script(7)
        self.assertIn("playlist: readPlaylistSlot(7)", script)

    def test_script_reads_native_player_name_owners_and_plain_client_names(self) -> None:
        script = CodolScoreboardTrace.build_script()
        self.assertEqual(CodolScoreboardTrace.PLAYER_NAME_CONFIGSTRING_BASE, 1975)
        self.assertIn("1975 + clientNum", script)
        self.assertIn("value_hex: valueHex", script)
        self.assertIn("function readCStringHex(address, maximum = 64)", script)
        self.assertIn("name_length: readU32(source.add(112))", script)
        self.assertIn("name: readClientInfoName(source)", script)
        self.assertIn("key.add(fullWordBytes + offset).readU8()", script)
        self.assertIn("player_name_configstrings: readPlayerNameConfigStrings()", script)

    def test_sample_only_disables_observer_installation(self) -> None:
        script = CodolScoreboardTrace.build_script(26, install_observers=False)
        self.assertIn("if (false) {", script)
        self.assertIn("observe('server_command'", script)

    def test_systeminfo_trace_is_targeted_and_read_only(self) -> None:
        script = CodolScoreboardTrace.build_script(
            install_observers=False,
            install_systeminfo_observers=True,
        )
        self.assertIn("event: 'systeminfo_enter'", script)
        self.assertIn("event: 'set_from_string_enter'", script)
        self.assertIn("event: 'set_variant_enter'", script)
        self.assertIn("targetSysteminfoDvars.has(state.name)", script)
        self.assertIn("event: 'poll_change'", script)
        self.assertIn("caller_rva: this.returnAddress.sub(module.base).toString()", script)
        self.assertIn("variant_words:", script)
        self.assertNotIn("writeU32", script)

    def test_summary_reports_equal_score_mirror(self) -> None:
        result = {
            "counts": {
                "server_command": 4,
                "update_score": 2,
                "copy_scoreboard_to_ui": 1,
                "populate_scoreboard_ui": 3,
                "score_view_update_score": 5,
                "score_view_initialize": 1,
                "score_view_update": 6,
                "view_manager_update": 7,
                "ingame_gfx_initialize": 1,
                "register_common_as_functions": 1,
                "register_score_view_as_function": 1,
                "register_sandd_view_as_function": 1,
                "sandd_view_initialize": 1,
                "sandd_view_build_state": 9,
            },
            "score_view_timer": {"elapsed_ms": 45000},
            "current": {
                "cgame": {"score_count": 2, "axis_score": 3, "allies_score": 1},
                "ui": {"score_count": 2, "axis_score": 3, "allies_score": 1},
            },
        }
        summary = CodolScoreboardTrace.summarize(result)
        self.assertEqual(summary["server_command_count"], 4)
        self.assertEqual(summary["score_view_update_score_count"], 5)
        self.assertEqual(summary["score_view_initialize_count"], 1)
        self.assertEqual(summary["score_view_update_count"], 6)
        self.assertEqual(summary["view_manager_update_count"], 7)
        self.assertEqual(summary["ingame_gfx_initialize_count"], 1)
        self.assertEqual(summary["register_common_as_functions_count"], 1)
        self.assertEqual(summary["register_score_view_as_function_count"], 1)
        self.assertEqual(summary["register_sandd_view_as_function_count"], 1)
        self.assertEqual(summary["sandd_view_initialize_count"], 1)
        self.assertEqual(summary["sandd_view_build_state_count"], 9)
        self.assertEqual(summary["score_view_elapsed_ms"], 45000)
        self.assertTrue(summary["score_mirror_comparable"])
        self.assertTrue(summary["score_mirror_equal"])

    def test_summary_reports_stale_score_mirror(self) -> None:
        result = {
            "counts": {},
            "current": {
                "cgame": {"score_count": 2, "axis_score": 2, "allies_score": 0},
                "ui": {"score_count": 2, "axis_score": 0, "allies_score": 0},
            },
        }
        summary = CodolScoreboardTrace.summarize(result)
        self.assertTrue(summary["score_mirror_comparable"])
        self.assertFalse(summary["score_mirror_equal"])


if __name__ == "__main__":
    unittest.main()
