#!/usr/bin/env python3

from __future__ import annotations

import unittest

from CodolFrameTrace import summarize_camera_rows


class CameraTraceSummaryTests(unittest.TestCase):
    def test_stable_camera_is_not_flagged(self) -> None:
        summary = summarize_camera_rows(
            [
                {
                    "event": "frame_sample",
                    "camera_diagnostics": {
                        "samples": 120,
                        "playing_samples": 120,
                        "alternating_frames": 0,
                        "max_origin_step": 0.01,
                        "max_angle_step": 0.02,
                        "max_axis_length_error": 0.001,
                        "max_axis_dot": 0.001,
                        "min_abs_axis_determinant": 0.999,
                        "playing_height_sum": 7200.0,
                        "tilted_samples": 0,
                    },
                }
            ]
        )
        self.assertEqual(summary["confidence"], "high")
        self.assertFalse(summary["camera_shake_detected"])
        self.assertFalse(summary["invalid_view_axis_detected"])
        self.assertFalse(summary["ground_level_camera_detected"])
        self.assertFalse(summary["persistent_roll_detected"])

    def test_alternating_tilted_ground_camera_is_flagged(self) -> None:
        summary = summarize_camera_rows(
            [
                {
                    "event": "frame_sample",
                    "camera_diagnostics": {
                        "samples": 60,
                        "playing_samples": 60,
                        "alternating_frames": 20,
                        "max_origin_step": 8.0,
                        "max_angle_step": 90.0,
                        "max_axis_length_error": 0.08,
                        "max_axis_dot": 0.2,
                        "min_abs_axis_determinant": 0.7,
                        "playing_height_sum": 480.0,
                        "tilted_samples": 60,
                    },
                }
            ]
        )
        self.assertTrue(summary["camera_shake_detected"])
        self.assertTrue(summary["invalid_view_axis_detected"])
        self.assertTrue(summary["ground_level_camera_detected"])
        self.assertTrue(summary["persistent_roll_detected"])
        self.assertEqual(summary["playing_height_average"], 8.0)

    def test_repeated_large_angle_steps_detect_non_aba_shake(self) -> None:
        summary = summarize_camera_rows(
            [
                {
                    "event": "frame_sample",
                    "camera_diagnostics": {
                        "samples": 120,
                        "playing_samples": 120,
                        "alternating_frames": 0,
                        "angle_alternating_frames": 0,
                        "origin_alternating_frames": 0,
                        "large_angle_steps": 3,
                        "max_angle_step": 60.0,
                        "min_abs_axis_determinant": 1.0,
                        "playing_height_sum": 7200.0,
                    },
                }
            ]
        )
        self.assertTrue(summary["camera_shake_detected"])
        self.assertEqual(summary["large_angle_steps"], 3)

    def test_prediction_summary_separates_snapshot_boundaries(self) -> None:
        summary = summarize_camera_rows(
            [
                {
                    "event": "frame_sample",
                    "camera_diagnostics": {
                        "samples": 120,
                        "playing_samples": 120,
                        "min_abs_axis_determinant": 1.0,
                        "playing_height_sum": 7200.0,
                    },
                    "prediction_diagnostics": {
                        "samples": 120,
                        "snapshot_advances": 20,
                        "discontinuities": 1,
                        "snapshot_gap_min_ms": 50,
                        "snapshot_gap_max_ms": 50,
                        "predicted_to_snap_sum": 1200.0,
                        "predicted_to_snap_max": 20.0,
                        "predicted_to_next_sum": 600.0,
                        "predicted_to_next_max": 12.0,
                        "snap_to_next_sum": 300.0,
                        "snap_to_next_max": 7.0,
                        "predicted_to_snap_angle_sum": 240.0,
                        "predicted_to_snap_angle_max": 4.0,
                        "predicted_to_next_angle_sum": 360.0,
                        "predicted_to_next_angle_max": 6.0,
                        "snap_to_next_angle_sum": 120.0,
                        "snap_to_next_angle_max": 2.0,
                        "snapshot_frame_steps": 20,
                        "snapshot_frame_step_sum": 80.0,
                        "snapshot_frame_step_max": 4.5,
                        "other_frame_steps": 100,
                        "other_frame_step_sum": 100.0,
                        "other_frame_step_max": 1.2,
                        "snapshot_frame_accelerations": 20,
                        "snapshot_frame_acceleration_sum": 60.0,
                        "snapshot_frame_acceleration_max": 3.5,
                        "other_frame_accelerations": 99,
                        "other_frame_acceleration_sum": 9.9,
                        "other_frame_acceleration_max": 0.2,
                        "snapshot_frame_angle_steps": 20,
                        "snapshot_frame_angle_step_sum": 30.0,
                        "snapshot_frame_angle_step_max": 2.0,
                        "other_frame_angle_steps": 100,
                        "other_frame_angle_step_sum": 100.0,
                        "other_frame_angle_step_max": 1.2,
                        "snapshot_frame_angle_accelerations": 20,
                        "snapshot_frame_angle_acceleration_sum": 10.0,
                        "snapshot_frame_angle_acceleration_max": 0.8,
                        "other_frame_angle_accelerations": 99,
                        "other_frame_angle_acceleration_sum": 19.8,
                        "other_frame_angle_acceleration_max": 0.4,
                        "snapshot_direction_reversals": 4,
                    },
                }
            ]
        )
        self.assertTrue(summary["snapshot_correlated_jitter_detected"])
        self.assertTrue(summary["camera_shake_detected"])
        self.assertEqual(summary["snapshot_advances"], 20)
        self.assertEqual(summary["prediction_discontinuities"], 1)
        self.assertEqual(summary["snapshot_gap_min_ms"], 50)
        self.assertEqual(summary["predicted_to_snap_average"], 10.0)
        self.assertEqual(summary["snapshot_frame_step_average"], 4.0)
        self.assertEqual(summary["other_frame_step_average"], 1.0)
        self.assertEqual(summary["predicted_to_snap_angle_average"], 2.0)
        self.assertEqual(summary["snap_to_next_angle_average"], 1.0)
        self.assertEqual(summary["snapshot_frame_angle_step_average"], 1.5)
        self.assertEqual(summary["other_frame_angle_step_average"], 1.0)


if __name__ == "__main__":
    unittest.main()
