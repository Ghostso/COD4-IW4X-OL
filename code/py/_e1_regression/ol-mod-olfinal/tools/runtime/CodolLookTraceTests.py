#!/usr/bin/env python3

from __future__ import annotations

import unittest

import CodolLookTrace


class CodolLookTraceTests(unittest.TestCase):
    def test_script_records_all_three_native_input_boundaries(self) -> None:
        script = CodolLookTrace.build_script()
        self.assertIn("Interceptor.attach(rawMouse", script)
        self.assertIn("Interceptor.attach(scaledMouse", script)
        self.assertIn("Interceptor.attach(createCmd", script)
        self.assertIn("source: 'client-native-observed'", script)
        self.assertIn("address.add(0x34C)", script)
        self.assertIn("address.add(0x270)", script)
        self.assertIn("address.add(0x298)", script)

    def test_dedicated_script_uses_versioned_observation_export(self) -> None:
        script = CodolLookTrace.build_dedicated_script(20)
        self.assertIn("CODOL_GameServerGetWorldPlayerSampleV2", script)
        self.assertIn("source: 'dedicated-authoritative-observed'", script)
        self.assertIn("viewangles: vec3(196)", script)
        self.assertIn("weapon_position_fraction: f32(268)", script)

    def test_summary_preserves_command_and_mouse_coverage(self) -> None:
        rows = [
            {"event": "armed"},
            {
                "event": "look_sample",
                "mouse": {"raw_output_edx": 0.0, "raw_output_esi": 2.0},
                "usercmd": {"command_time": 100},
                "camera": {},
            },
            {
                "event": "look_sample",
                "mouse": {"raw_output_edx": 0.0, "raw_output_esi": 0.0},
                "usercmd": {"command_time": 116},
                "camera": {},
            },
        ]
        self.assertEqual(
            CodolLookTrace.summarize(rows),
            {
                "sample_count": 2,
                "mouse_input_sample_count": 1,
                "command_time_first": 100,
                "command_time_last": 116,
                "command_time_monotonic": True,
                "camera_sample_count": 2,
                "dedicated_sample_count": 0,
            },
        )

    def test_summary_quantifies_yaw_input_and_snapshot_correction(self) -> None:
        def sample(
            client_yaw: float,
            refdef_yaw: float,
            predicted_yaw: float,
            snapshot_yaw: float,
            raw: int,
            scaled: float,
            pm_flags: int,
        ) -> dict:
            return {
                "event": "look_sample",
                "mouse": {
                    "raw_output_edx": 0,
                    "raw_output_esi": raw,
                    "scaled_0": scaled,
                },
                "client_viewangles": [0.0, client_yaw, 0.0],
                "dvars": {"m_yaw_candidate": {"current_float": 0.022}},
                "usercmd": {"command_time": 100},
                "camera": {
                    "predicted": {
                        "viewangles": [0.0, predicted_yaw, 0.0],
                        "pm_flags": pm_flags,
                    },
                    "snapshot": {"viewangles": [0.0, snapshot_yaw, 0.0]},
                    "refdef_viewangles": [0.0, refdef_yaw, 0.0],
                },
            }

        summary = CodolLookTrace.summarize(
            [
                sample(0.0, 0.0, 0.0, 0.0, 0, 0.0, 0),
                sample(-0.22, -0.20, -0.3, -0.1, 2, 10.0, 0),
                sample(-0.66, -0.60, -0.8, -0.4, 4, 20.0, 0x4000),
            ]
        )
        metrics = summary["yaw_metrics"]
        self.assertEqual(metrics["mouse_yaw_sample_count"], 2)
        self.assertEqual(metrics["scaled_yaw_per_raw_min"], 5.0)
        self.assertEqual(metrics["scaled_yaw_per_raw_max"], 5.0)
        self.assertAlmostEqual(metrics["input_projection_residual_max"], 0.0)
        self.assertAlmostEqual(metrics["predicted_snapshot_yaw_error_max"], 0.4)
        self.assertAlmostEqual(metrics["render_yaw_step_max"], 0.4)
        self.assertEqual(metrics["sprint_render_yaw_sample_count"], 1)
        self.assertAlmostEqual(metrics["sprint_render_yaw_step_max"], 0.4)
        self.assertAlmostEqual(metrics["non_sprint_render_yaw_step_max"], 0.2)


if __name__ == "__main__":
    unittest.main()
