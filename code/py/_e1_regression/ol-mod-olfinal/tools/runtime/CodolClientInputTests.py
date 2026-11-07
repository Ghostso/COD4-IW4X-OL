#!/usr/bin/env python3
"""Focused tests for CODOL native-input capture integrity."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from CodolClientInput import (
    OPAQUE_DATA_KEY,
    RAW_SAMPLE_FORMAT,
    RawSampleCheckpoint,
    _record_terminal_payload,
    build_scenario_script,
    build_script,
    capture_summary,
    load_raw_sample_checkpoint,
    prepare_opaque_sample,
    raw_sample_checkpoint_path,
    summarize_raw_sample_checkpoint,
    write_result_checkpoint,
)
from CodolInputScenario import (
    ACTION_NAMES,
    normalize_scenario,
    scenario_duration_seconds,
    single_action_scenario,
)


def parser_summary() -> dict[str, int]:
    return {
        "snapshot_enter_count": 3,
        "snapshot_leave_count": 3,
        "playerstate_enter_count": 3,
        "playerstate_leave_count": 3,
        "server_message_enter_count": 3,
        "server_message_leave_count": 3,
        "packet_event_leave_count": 3,
        "accepted_packet_count": 3,
        "rejected_packet_count": 0,
        "overflow_events": 0,
        "com_error_count": 0,
    }


def opaque_sample(sequence: int, data: bytes) -> dict[str, object]:
    return {
        "event": "server-sample",
        "sequence": sequence,
        "phase": "running",
        "parser_summary": parser_summary(),
        "opaque_evidence_segments": [
            {
                "kind": "server-world-player-sample-v1",
                "offset": 0,
                "size": len(data),
                "schema_version": 1,
            }
        ],
        OPAQUE_DATA_KEY: data,
    }


class CodolClientInputTests(unittest.TestCase):
    def assert_javascript_parses(self, source: str) -> None:
        completed = subprocess.run(
            ["node", "--check", "-"],
            input=f"(function(){{\n{source}\n}})();\n",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(shutil.which("node"), "node is required for generated JS check")
    def test_generated_javascript_parses_for_paired_and_momentary_actions(self) -> None:
        for action in ("attack", "weapnext"):
            self.assert_javascript_parses(build_script(action, 0, 0.1, 0.5, 0.05))

    def test_scenario_normalization_supports_overlapping_actions(self) -> None:
        scenario = normalize_scenario(
            {
                "version": 1,
                "name": "move-crouch",
                "events": [
                    {"at_ms": 0, "action": "forward", "transition": "down"},
                    {"at_ms": 50, "action": "crouch", "transition": "down"},
                    {"at_ms": 100, "action": "crouch", "transition": "up"},
                    {"at_ms": 200, "action": "forward", "transition": "up"},
                ],
                "observe_after_ms": 300,
            }
        )
        self.assertEqual(scenario["duration_ms"], 500)
        released = normalize_scenario(
            {
                "version": 1,
                "name": "spawn-release-then-forward",
                "events": [
                    {"at_ms": 0, "action": "forward", "transition": "release"},
                    {"at_ms": 250, "action": "forward", "transition": "down"},
                    {"at_ms": 500, "action": "forward", "transition": "up"},
                ],
            }
        )
        self.assertEqual(released["events"][0]["transition"], "release")
        dive = normalize_scenario(
            {
                "version": 1,
                "name": "sprint-dive",
                "events": [
                    {"at_ms": 0, "action": "forward", "transition": "down"},
                    {"at_ms": 50, "action": "sprint", "transition": "down"},
                    {"at_ms": 500, "action": "prone", "transition": "down"},
                    {"at_ms": 600, "action": "prone", "transition": "up"},
                    {"at_ms": 900, "action": "sprint", "transition": "up"},
                    {"at_ms": 950, "action": "forward", "transition": "up"},
                ],
            }
        )
        self.assertEqual(dive["duration_ms"], 950)
        with self.assertRaisesRegex(ValueError, "explicitly release"):
            normalize_scenario(
                {
                    "version": 1,
                    "name": "stuck-key",
                    "events": [
                        {"at_ms": 0, "action": "forward", "transition": "down"}
                    ],
                }
            )
        with self.assertRaisesRegex(ValueError, "after its press"):
            normalize_scenario(
                {
                    "version": 1,
                    "name": "same-frame-pulse",
                    "events": [
                        {"at_ms": 0, "action": "forward", "transition": "down"},
                        {"at_ms": 0, "action": "forward", "transition": "up"},
                    ],
                }
            )
        with self.assertRaisesRegex(ValueError, "must use 'up'"):
            normalize_scenario(
                {
                    "version": 1,
                    "name": "release-active-action",
                    "events": [
                        {"at_ms": 0, "action": "forward", "transition": "down"},
                        {
                            "at_ms": 100,
                            "action": "forward",
                            "transition": "release",
                        },
                    ],
                }
            )

    def test_single_action_scenario_preserves_legacy_timing(self) -> None:
        scenario = single_action_scenario("forward", 0.25, 0.75)
        self.assertEqual(scenario["duration_ms"], 1000)
        self.assertAlmostEqual(scenario_duration_seconds(scenario), 1.0)
        self.assertEqual(scenario["events"][1]["at_ms"], 250)

    def test_action_names_follow_the_codol_binding_table(self) -> None:
        self.assertEqual(ACTION_NAMES["ads"][:2], ("+speed_throw", "-speed_throw"))
        self.assertEqual(
            ACTION_NAMES["sprint"][:2],
            ("+breath_sprint", "-breath_sprint"),
        )
        self.assertEqual(ACTION_NAMES["reload"][:2], ("+reload", "-reload"))
        self.assertEqual(ACTION_NAMES["turnleft"][:2], ("+left", "-left"))
        self.assertEqual(ACTION_NAMES["turnright"][:2], ("+right", "-right"))

    def test_script_finishes_directly_without_a_second_capture_protocol(self) -> None:
        source = build_script("jump", 0, 0.1, 0.5, 0.05)
        complete_block = source.split("function complete()", 1)[1].split(
            "function abort", 1
        )[0]
        self.assertIn("finish('completed', null)", complete_block)
        self.assertIn("phase = 'pending-start'", source)
        self.assertNotIn("finalizecapture", source)
        self.assertNotIn("PmoveCapture", source)
        self.assertNotIn("pmove_capture", source)
        self.assertIn("opaque_client_playerstate: true", source)
        self.assertNotIn("sample.add(60).readU32()", source)

    def test_low_interference_script_does_not_install_entity_parser_hooks(self) -> None:
        source = build_script(
            "forward", 0, 0.1, 0.5, 0.05, trace_parser=False
        )
        self.assertIn("if (false) {\nInterceptor.attach(clParsePacketEntities", source)
        self.assertIn("parser_trace: false", source)
        self.assertIn("Interceptor.attach(comFrame", source)

        traced_source = build_script(
            "forward", 0, 0.1, 0.5, 0.05, trace_parser=True
        )
        self.assertIn("if (true) {\nInterceptor.attach(clParsePacketEntities", traced_source)

    @unittest.skipUnless(shutil.which("node"), "node is required for generated JS check")
    def test_release_prelude_uses_the_native_up_action(self) -> None:
        scenario = normalize_scenario(
            {
                "version": 1,
                "name": "spawn-release-then-forward",
                "events": [
                    {"at_ms": 0, "action": "forward", "transition": "release"},
                    {"at_ms": 250, "action": "forward", "transition": "down"},
                    {"at_ms": 500, "action": "forward", "transition": "up"},
                ],
            }
        )
        source = build_scenario_script(scenario, 0, 0.05)
        self.assert_javascript_parses(source)
        self.assertIn("transition === 'up' || transition === 'release'", source)
        self.assertIn("'input-release'", source)

    def test_opaque_binary_attachment_is_preserved_and_summarized(self) -> None:
        payload = {
            "event": "server-sample",
            "sequence": 0,
            "parser_summary": parser_summary(),
            "opaque_evidence_segments": [
                {
                    "kind": "server-world-player-sample-v1",
                    "offset": 0,
                    "size": 8,
                    "schema_version": 1,
                },
                {
                    "kind": "client-predicted-playerstate",
                    "offset": 8,
                    "size": 8,
                },
            ],
        }
        sample, errors = prepare_opaque_sample(payload, b"0123456789abcdef", 0)
        self.assertEqual(errors, [])
        self.assertEqual(sample[OPAQUE_DATA_KEY], b"0123456789abcdef")
        summary = capture_summary([sample])
        self.assertTrue(summary["sequence_contiguous"])
        self.assertTrue(summary["segment_framing_valid"])
        self.assertEqual(summary["opaque_evidence_count"], 1)
        self.assertEqual(summary["opaque_evidence_bytes"], 16)
        self.assertEqual(summary["latest_envelope"]["schema_version"], 1)
        self.assertEqual(summary["latest_parser_summary"], parser_summary())

        projected = dict(sample)
        projected["state_projection"] = {
            "server": {"origin": [1.0, 2.0, 3.0]},
            "predicted": {"origin": [4.0, 5.0, 6.0]},
            "snapshot": {"origin": [4.0, 5.0, 6.0]},
        }
        moved = dict(projected)
        moved["sequence"] = 1
        moved["state_projection"] = {
            "server": {"origin": [11.0, 2.0, 3.0]},
            "predicted": {"origin": [14.0, 5.0, 6.0]},
            "snapshot": {"origin": [14.0, 5.0, 6.0]},
        }
        projected_summary = capture_summary([projected, moved])
        self.assertEqual(projected_summary["origin_spans"]["server"], [10.0, 0.0, 0.0])
        self.assertEqual(
            projected_summary["origin_spans"]["predicted"], [10.0, 0.0, 0.0]
        )
        self.assertEqual(
            projected_summary["latest_state_projection"], moved["state_projection"]
        )

        _, missing_errors = prepare_opaque_sample(payload, None, 0)
        self.assertTrue(any("missing" in error for error in missing_errors))
        _, sequence_errors = prepare_opaque_sample(payload, b"0123456789abcdef", 1)
        self.assertTrue(any("sequence" in error for error in sequence_errors))

    def test_timeout_failure_latch_rejects_late_completion(self) -> None:
        result: dict[str, object] = {
            "ok": False,
            "final_event": "timeout-release-requested",
        }
        _record_terminal_payload(
            result,
            {
                "ok": True,
                "event": "completed",
                "parser_summary": {"overflow_events": 0},
            },
            failure_latched=True,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["final_event"], "timeout-release-requested")
        self.assertEqual(result["late_terminal_event"], "completed")

    def test_checkpoint_reports_only_capture_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "client_input.json"
            write_result_checkpoint(
                output,
                {"ok": False, "final_event": "timeout-release-requested"},
                [opaque_sample(0, b"sample")],
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["capture_summary"]["sample_count"], 1)
            self.assertTrue(payload["capture_summary"]["sequence_contiguous"])
            self.assertNotIn("server_summary", payload)
            self.assertNotIn("gameplay", payload["capture_summary"])

    def test_raw_checkpoint_sidecar_hashes_offsets_and_recoverable_tails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "client_input.json"
            raw_path = raw_sample_checkpoint_path(output)
            scenario = single_action_scenario("forward", 0.1, 0.2)
            samples = [opaque_sample(0, b"one"), opaque_sample(1, b"two-two")]
            raw = RawSampleCheckpoint(raw_path, scenario)
            write_result_checkpoint(output, {"ok": False}, samples, raw)

            self.assertEqual(raw.blob_path.read_bytes(), b"onetwo-two")
            self.assertNotIn(OPAQUE_DATA_KEY, raw_path.read_text(encoding="utf-8"))
            recovered = load_raw_sample_checkpoint(raw_path)
            descriptors = [sample["opaque_evidence"] for sample in recovered["samples"]]
            self.assertEqual([item["offset"] for item in descriptors], [0, 3])
            self.assertEqual([item["size"] for item in descriptors], [3, 7])
            self.assertEqual(
                descriptors[0]["sha256"], hashlib.sha256(b"one").hexdigest()
            )
            self.assertEqual(recovered["orphan_blob_bytes"], 0)
            self.assertTrue(summarize_raw_sample_checkpoint(raw_path)["integrity_complete"])

            with raw.blob_path.open("ab") as stream:
                stream.write(b"x")
            orphan = load_raw_sample_checkpoint(raw_path)
            self.assertEqual(orphan["orphan_blob_bytes"], 1)
            self.assertFalse(
                summarize_raw_sample_checkpoint(raw_path)["integrity_complete"]
            )

            raw.blob_path.write_bytes(b"onetwo-two")
            with raw_path.open("ab") as stream:
                stream.write(b'{"record":"sample"')
            tail = summarize_raw_sample_checkpoint(raw_path)
            self.assertTrue(tail["raw_samples"]["incomplete_tail_ignored"])
            self.assertFalse(tail["integrity_complete"])

    def test_raw_checkpoint_rejects_corrupt_blob_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samples.jsonl"
            raw = RawSampleCheckpoint(path, single_action_scenario("forward", 0.1, 0.2))
            raw.checkpoint([opaque_sample(0, b"evidence")])
            raw.blob_path.write_bytes(b"EVIDENCE")
            with self.assertRaisesRegex(ValueError, "hash is invalid"):
                load_raw_sample_checkpoint(path)

    def test_schema_one_raw_checkpoint_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.samples.jsonl"
            scenario = single_action_scenario("forward", 0.1, 0.2)
            records = [
                {
                    "record": "header",
                    "format": RAW_SAMPLE_FORMAT,
                    "schema_version": 1,
                    "scenario": scenario,
                },
                {"record": "sample", "index": 0, "sample": {"sequence": 0}},
            ]
            path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            recovered = load_raw_sample_checkpoint(path)
            self.assertEqual(recovered["schema_version"], 1)
            self.assertEqual(recovered["recovered_sample_count"], 1)
            offline = summarize_raw_sample_checkpoint(path)
            self.assertTrue(offline["recovery_ok"])
            self.assertFalse(offline["integrity_complete"])

    def test_raw_and_summary_checkpoints_are_serialized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "client_input.json"
            raw = RawSampleCheckpoint(
                raw_sample_checkpoint_path(output),
                single_action_scenario("forward", 0.1, 0.2),
            )
            samples = [opaque_sample(0, b"a"), opaque_sample(1, b"b")]
            errors: list[BaseException] = []

            def write(count: int) -> None:
                try:
                    write_result_checkpoint(output, {"ok": False}, samples[:count], raw)
                except BaseException as error:
                    errors.append(error)

            first = threading.Thread(target=write, args=(1,))
            second = threading.Thread(target=write, args=(2,))
            first.start()
            first.join(2.0)
            second.start()
            second.join(2.0)
            self.assertEqual(errors, [])
            self.assertEqual(load_raw_sample_checkpoint(raw.path)["recovered_sample_count"], 2)
            checkpoint = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["raw_samples"]["persisted_sample_count"], 2)

    def test_scenario_snapshot_hash_is_checked_before_attach(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario_path = Path(directory) / "scenario.json"
            scenario_path.write_text(
                json.dumps(single_action_scenario("forward", 0.1, 0.2)),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("CodolClientInput.py")),
                    "--scenario",
                    str(scenario_path),
                    "--scenario-sha256",
                    "0" * 64,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("does not match", completed.stderr)


if __name__ == "__main__":
    unittest.main()
