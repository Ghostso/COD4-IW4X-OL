#!/usr/bin/env python3
"""Regression tests for CODOL scene-model trace reporting."""

from __future__ import annotations

import unittest

from CodolSceneModelTrace import build_script, build_summary


class SceneModelTraceSummaryTests(unittest.TestCase):
    def test_player_dobj_trace_uses_confirmed_entity_weapon_offsets(self) -> None:
        script = build_script(1.0)
        self.assertIn("entity_weapon_asset_index = entityState.add(0xD0)", script)
        self.assertIn(
            "entity_presentation_weapon_asset_index =\n"
            "            entityState.add(0xD2)",
            script,
        )
        self.assertNotIn("state.entity_weapon =", script)

    def test_player_dobj_trace_captures_world_character_models(self) -> None:
        script = build_script(1.0)
        self.assertIn("characterInfo.add(0x18)", script)
        self.assertIn("characterInfo.add(0x20), 10", script)
        self.assertIn("characterInfo.add(0x48), 10", script)
        self.assertIn("characterInfo.add(0x1F4).readU32()", script)
        self.assertIn("characterInfo.add(0x320).readPointer()", script)
        self.assertIn("Interceptor.attach(bgPlayerAnimation", script)

    def test_script_model_trace_captures_final_visibility_inputs(self) -> None:
        script = build_script(1.0)
        self.assertIn("render_control_0x160", script)
        self.assertIn("dobj_num_bones_0x0A", script)
        self.assertIn("dobj_flags_0x0B", script)
        self.assertIn("dobj_scale_0xC8", script)
        self.assertIn("pose_origin: poseOrigins.get", script)

    def test_dobj_scan_captures_pose_matrix_summary(self) -> None:
        script = build_script(1.0)
        self.assertIn("dobj.add(148).readU32()", script)
        self.assertIn("dobj.add(152).readPointer()", script)
        self.assertIn("matrix.add(16).readFloat()", script)
        self.assertIn("nonzero_translation_count", script)
        self.assertIn("nonzero_quaternion_count", script)
        self.assertIn("nonzero_trans_weight_count", script)
        self.assertIn("readDObjBindPoseSummary", script)
        self.assertIn("Interceptor.attach(dobjCalcPose", script)
        self.assertIn("Interceptor.attach(dobjCalcSkel", script)
        self.assertIn("serverEntityByDObj.set(dobj.toString(), entityIndex)", script)
        self.assertIn("bind_pose: readDObjBindPoseSummary(dobj)", script)
        self.assertIn("part_bits: readDObjPartBits(dobj)", script)
        self.assertIn("scale: dobj.add(0xC8).readFloat()", script)

    def test_pose_stage_capture_targets_requested_entity(self) -> None:
        script = build_script(1.0, 7)
        self.assertIn("const poseEntity = 7", script)
        self.assertIn("isRequestedPoseEntity(this.dobj)", script)
        self.assertIn("owner_kind:", script)
        self.assertIn("owner_entity:", script)
        self.assertIn("serverEntityByDObj.set(this.dobj.toString(), entityIndex)", script)
        self.assertIn("attachDObjCalcSkelWrapper", script)
        self.assertIn("Interceptor.attach(dobjCalcAnim", script)
        self.assertIn("Interceptor.attach(dobjCalcModelHierarchy", script)

    def test_reports_compact_counts(self) -> None:
        result = {
            "pid": 123,
            "ok": True,
            "calls": 170182,
            "creates": 203,
            "wrapper_creates": 203,
            "existing_dobjs": [{}, {}],
            "existing_server_dobjs": [{}],
            "player_dobj_updates": [{}, {}, {}],
            "player_animation_updates": [{}, {}],
            "dobj_calc_pose_updates": [{}, {}],
            "dobj_calc_skel_updates": [{}, {}, {}],
            "dobj_calc_skel_raw_calls": 5,
            "dobj_calc_skel_main_thread_calls": 4,
            "dobj_calc_skel_worker_thread_calls": 1,
            "dobj_calc_skel_wrapper_updates": [{}, {}],
            "dobj_calc_anim_calls": 5,
            "dobj_calc_anim_updates": [{}, {}, {}],
            "dobj_calc_hierarchy_calls": 15,
            "dobj_calc_hierarchy_updates": [{}, {}, {}, {}],
            "world_character_model_resolutions": [{}, {}],
            "script_mover_entities": [{}, {}, {}],
            "models": [{}, {}, {}, {}],
            "invalid_dobjs": 0,
        }

        self.assertEqual(
            build_summary(result),
            {
                "pid": 123,
                "ok": True,
                "calls": 170182,
                "creates": 203,
                "wrapper_creates": 203,
                "existing_dobjs": 2,
                "existing_server_dobjs": 1,
                "player_dobj_updates": 3,
                "player_animation_updates": 2,
                "dobj_calc_pose_updates": 2,
                "dobj_calc_skel_updates": 3,
                "dobj_calc_skel_raw_calls": 5,
                "dobj_calc_skel_main_thread_calls": 4,
                "dobj_calc_skel_worker_thread_calls": 1,
                "dobj_calc_skel_wrapper_updates": 2,
                "dobj_calc_anim_calls": 5,
                "dobj_calc_anim_updates": 3,
                "dobj_calc_hierarchy_calls": 15,
                "dobj_calc_hierarchy_updates": 4,
                "world_character_model_resolutions": 2,
                "script_movers": 3,
                "unique_models": 4,
                "invalid_dobjs": 0,
            },
        )

    def test_reports_failure_without_trace_arrays(self) -> None:
        self.assertEqual(
            build_summary({"pid": 456, "ok": False, "error": "capture timed out"}),
            {
                "pid": 456,
                "ok": False,
                "calls": 0,
                "creates": 0,
                "wrapper_creates": 0,
                "existing_dobjs": 0,
                "existing_server_dobjs": 0,
                "player_dobj_updates": 0,
                "player_animation_updates": 0,
                "dobj_calc_pose_updates": 0,
                "dobj_calc_skel_updates": 0,
                "dobj_calc_skel_raw_calls": 0,
                "dobj_calc_skel_main_thread_calls": 0,
                "dobj_calc_skel_worker_thread_calls": 0,
                "dobj_calc_skel_wrapper_updates": 0,
                "dobj_calc_anim_calls": 0,
                "dobj_calc_anim_updates": 0,
                "dobj_calc_hierarchy_calls": 0,
                "dobj_calc_hierarchy_updates": 0,
                "world_character_model_resolutions": 0,
                "script_movers": 0,
                "unique_models": 0,
                "invalid_dobjs": 0,
                "error": "capture timed out",
            },
        )

    def test_world_character_model_resolver_trace_records_native_abi(self) -> None:
        script = build_script(1.0)
        self.assertIn("this.context.eax.toInt32()", script)
        self.assertIn("this.output = args[0]", script)
        self.assertIn("this.selectionIds = args[1]", script)
        self.assertIn("this.female = args[2].toInt32()", script)
        self.assertIn("this.color = args[3].toInt32()", script)
        self.assertIn("worldCharacterModelSlotBases.add(slot * 4).readU16()", script)
        self.assertIn("for (let index = 0; index < 11; ++index)", script)


if __name__ == "__main__":
    unittest.main()
