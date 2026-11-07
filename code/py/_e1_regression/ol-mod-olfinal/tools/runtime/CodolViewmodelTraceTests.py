#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
import unittest

from CodolViewmodelTrace import build_script, diagnose


class CodolViewmodelTraceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is required for generated JS syntax check")
    def test_generated_javascript_parses(self) -> None:
        source = f"(function(){{\n{build_script(64)}\n}})();\n"
        completed = subprocess.run(
            ["node", "--check", "-"],
            input=source,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_model_candidates_are_embedded_as_json(self) -> None:
        source = build_script(8, ('viewhands_tf141', 'quote"candidate'))
        self.assertIn(
            '["viewhands_tf141", "quote\\\"candidate"]',
            source,
        )
        self.assertIn("viewmodel_config_strings: scanViewmodelConfigStrings()", source)
        self.assertIn("weapon_config_strings: scanWeaponConfigStrings()", source)
        self.assertIn("weapon_count_config_string: readRawConfigString(6800)", source)
        self.assertIn("dynamic_config_string: dynamicValue", source)
        self.assertIn("first_dynamic_weapon_config_string_types: Array.from", source)
        self.assertIn("hud_weapon_name_returns: hudWeaponNameReturns", source)
        self.assertIn("Interceptor.attach(addresses.get_hud_weapon_name", source)
        self.assertIn("Interceptor.attach(addresses.build_modular_model_table", source)
        self.assertIn("model_0x2c: readModel(readPointer(definition.add(0x2C)))", source)
        self.assertIn("model_0x34: readModel(readPointer(definition.add(0x34)))", source)
        self.assertIn("Interceptor.attach(addresses.resolve_base_models", source)
        self.assertIn("Interceptor.attach(addresses.resolve_attachment_models", source)
        self.assertIn("Interceptor.attach(addresses.update_character_viewmodel", source)
        self.assertIn("Interceptor.attach(addresses.resolve_character_models", source)
        self.assertIn("Interceptor.attach(addresses.unpack_character_selection", source)
        self.assertIn("Interceptor.attach(addresses.convert_client_info", source)
        self.assertIn("Interceptor.attach(addresses.transform_character_selection", source)
        self.assertIn("Interceptor.attach(addresses.resolve_xmodel", source)
        self.assertIn("character_samples: characterSamples", source)
        self.assertIn("convertedClientInfos.set(this.clientNum, this.output)", source)
        self.assertIn("clientRecord.add(924)", source)
        self.assertIn("netState.add(292)", source)
        self.assertIn("this.faction = this.context.eax.toUInt32()", source)
        self.assertIn("attachment_count: attachmentCount", source)
        self.assertIn("definition.add(0xFF0 + index * 36)", source)
        self.assertIn("(34720 + 1173 * nativeDefinitionIndex) * 4", source)
        self.assertIn("['int'],\n    'fastcall'", source)

    def test_diagnoses_missing_dobj(self) -> None:
        payload = {
            "counts": {
                "add_view_weapon": 20,
                "add_player_weapon": 20,
                "add_viewmodel_dobj_to_scene": 20,
                "add_viewmodel_dobj_to_scene_nonnull": 0,
            },
            "weapon_index_returns": {"165": 40},
        }
        self.assertEqual(diagnose(payload)["result"], "viewmodel_dobj_missing")

    def test_diagnoses_scene_submission(self) -> None:
        payload = {
            "counts": {
                "add_view_weapon": 20,
                "add_player_weapon": 20,
                "add_viewmodel_dobj_to_scene": 20,
                "add_viewmodel_dobj_to_scene_nonnull": 20,
                "validate_viewmodel_scene_dobj": 20,
                "validate_viewmodel_scene_dobj_accepted": 20,
            },
            "weapon_index_returns": {"165": 40},
        }
        self.assertEqual(
            diagnose(payload)["result"],
            "viewmodel_submitted_to_scene",
        )

    def test_diagnoses_submitted_tag_origin_placeholder(self) -> None:
        payload = {
            "counts": {
                "add_view_weapon": 20,
                "add_player_weapon": 20,
                "add_viewmodel_dobj_to_scene": 20,
                "add_viewmodel_dobj_to_scene_nonnull": 20,
                "validate_viewmodel_scene_dobj": 20,
                "validate_viewmodel_scene_dobj_accepted": 20,
            },
            "weapon_index_returns": {"165": 40},
            "samples": [
                {
                    "kind": "create_client_dobj",
                    "value": {
                        "models": [
                            {"model": {"name": "tag_origin"}},
                        ]
                    },
                }
            ],
        }
        diagnosis = diagnose(payload)
        self.assertEqual(diagnosis["result"], "viewmodel_placeholder_only")
        self.assertEqual(diagnosis["created_model_names"], ["tag_origin"])

    def test_diagnoses_ac130_hud_weapon_name_independently(self) -> None:
        payload = {
            "counts": {
                "add_view_weapon": 1,
                "add_player_weapon": 1,
                "add_viewmodel_dobj_to_scene": 1,
                "add_viewmodel_dobj_to_scene_nonnull": 1,
                "hud_utility_update": 3,
            },
            "weapon_index_returns": {"289": 2},
            "hud_weapon_name_returns": {
                "ac130_25mm_mp": 2,
                "m4_mp": 1,
            },
        }
        diagnosis = diagnose(payload)
        self.assertTrue(diagnosis["hud_utility_seen"])
        self.assertTrue(diagnosis["ac130_hud_weapon_seen"])
        self.assertEqual(
            diagnosis["observed_hud_weapon_names"],
            ["ac130_25mm_mp", "m4_mp"],
        )

    def test_diagnoses_character_model_path_independently(self) -> None:
        payload = {
            "counts": {
                "update_character_viewmodel": 2,
                "resolve_character_models": 1,
                "change_viewmodel_dobj_from_character": 1,
            },
            "character_samples": [
                {
                    "kind": "resolve_character_xmodel",
                    "value": {
                        "model": {"name": "han_magie_ss_f_vmchar_00"},
                    },
                },
                {
                    "kind": "resolve_character_xmodel",
                    "value": {
                        "model": {"name": "fja_SHEprestigeA_ss_f_vmchar_00"},
                    },
                },
            ],
        }
        diagnosis = diagnose(payload)
        self.assertTrue(diagnosis["character_viewmodel_update_seen"])
        self.assertTrue(diagnosis["character_model_resolver_seen"])
        self.assertTrue(diagnosis["character_dobj_rebuild_seen"])
        self.assertEqual(
            diagnosis["resolved_character_model_names"],
            [
                "fja_SHEprestigeA_ss_f_vmchar_00",
                "han_magie_ss_f_vmchar_00",
            ],
        )


if __name__ == "__main__":
    unittest.main()
