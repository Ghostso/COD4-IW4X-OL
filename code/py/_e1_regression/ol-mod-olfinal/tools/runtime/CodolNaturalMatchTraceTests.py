#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from CodolCaptureEvidence import OPAQUE_DATA_KEY, capture_summary
from CodolClientInput import RawSampleCheckpoint
from CodolMatchFlow import (
    CURRENT_CHARACTER_SELECT_ITEM_RVA,
    build_script as build_match_script,
)
from CodolInputScenario import load_scenario, single_action_scenario
from CodolNaturalMatchTrace import (
    CommandFailure,
    forced_command_target_satisfied,
    forced_loadout_available,
    reliable_sequence_advanced,
    normalize_reliable_command,
    ManagedProcess,
    NaturalMatchTrace,
    ProtocolFailure,
    ProtocolProgressTracker,
    WorkflowTimeout,
    allocation_source_allowed,
    active_world_reusable,
    input_parser_boundary_complete,
    json_objects,
    parse_args,
    parser_trace_status,
    powershell_file_command,
    quick_match_frontend_ready,
    world_boundary_reached,
)


def test_args(output: Path) -> argparse.Namespace:
    return argparse.Namespace(
        game_dir=Path(r"C:\CODOL"),
        output_dir=output,
        playlist_id=26,
        character_index=None,
        install=False,
        skip_build=False,
        mode="release",
        clean_launch=False,
        keep_game_running=True,
        keep_server_watcher_running=False,
        watch_damage_entity_num=[],
        require_active_world=False,
        launch_mode="auto",
        launch_wait=1.0,
        frontend_timeout=1.0,
        reuse_frontend_timeout=1.0,
        frontend_stable_seconds=0.0,
        trace_ready_timeout=1.0,
        match_timeout=1.0,
        force_client_allocation=False,
        gamestate_timeout=1.0,
        post_gamestate_seconds=0.0,
        forced_reliable_command=None,
        forced_command_timeout=1.0,
        viewmodel_trace=False,
        viewmodel_trace_seconds=0.2,
        input_action=None,
        input_scenario=None,
        input_scenario_payload=None,
        input_hold_seconds=0.1,
        input_observe_seconds=0.2,
        input_sample_interval=0.05,
        frame_trace=False,
        traffic_stall_seconds=10.0,
        progress_interval=5.0,
        sample_interval=1.0,
        build_timeout=1.0,
    )


def fake_process(output: Path, name: str) -> ManagedProcess:
    stdout_path = output / f"{name}.stdout.log"
    stderr_path = output / f"{name}.stderr.log"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    process = MagicMock()
    process.poll.return_value = None
    process.returncode = 0
    stdout_stream = stdout_path.open("a", encoding="utf-8")
    stderr_stream = stderr_path.open("a", encoding="utf-8")
    return ManagedProcess(process, stdout_path, stderr_path, stdout_stream, stderr_stream)


def complete_input_capture_payload(
    output: Path,
    scenario: dict[str, Any],
    *,
    scenario_sha256: str | None = None,
) -> dict[str, Any]:
    parser = {
        "overflow_events": 0,
        "com_error_count": 0,
        "server_message_enter_count": 3,
        "server_message_leave_count": 3,
        "packet_event_leave_count": 3,
        "accepted_packet_count": 3,
    }
    opaque = b"opaque-evidence"
    raw_path = output.with_suffix(".samples.jsonl").resolve()
    blob_path = raw_path.with_suffix(".bin")
    sample = {
        "ok": True,
        "event": "server-sample",
        "sequence": 0,
        "phase": "observing",
        "parser_summary": parser,
        "opaque_evidence_segments": [
            {
                "kind": "server-world-player-sample-v1",
                "offset": 0,
                "size": len(opaque),
                "schema_version": 1,
            }
        ],
        OPAQUE_DATA_KEY: opaque,
    }
    raw_checkpoint = RawSampleCheckpoint(raw_path, scenario)
    raw_checkpoint.checkpoint([sample])
    scenario_timing = {
        "valid": True,
        "overdue_event_group_count": 0,
        "dispatched_event_group_count": len(
            {int(event["at_ms"]) for event in scenario["events"]}
        ),
    }
    payload: dict[str, Any] = {
        "ok": True,
        "final_event": "completed",
        "events": [
            {
                "ok": True,
                "event": "armed",
            },
            *[
                {
                    "ok": True,
                    "event": (
                        "input-activate"
                        if event["transition"] == "activate"
                        else "input-down"
                        if event["transition"] == "down"
                        else "input-release"
                        if event["transition"] == "release"
                        else "input-up"
                    ),
                    "scenario_event_index": index,
                    "action": event["action"],
                    "transition": event["transition"],
                }
                for index, event in enumerate(scenario["events"])
            ],
            {
                "ok": True,
                "event": "completed",
                "parser_summary": parser,
                "scenario_timing": scenario_timing,
            },
        ],
        "process_exited": False,
        "process_alive_after_observation": True,
        "parser_summary": parser,
        "scenario_timing": scenario_timing,
        "capture_summary": capture_summary([sample]),
        "raw_samples": raw_checkpoint.status(),
        # The parent must ignore domain diagnostics and only gate raw evidence integrity.
        "legacy_gameplay_diagnostics": {"prediction_error": 9999, "weapon": -1},
    }
    if scenario_sha256 is not None:
        payload["scenario_source_sha256"] = scenario_sha256
    return payload


class NaturalMatchTraceTests(unittest.TestCase):
    def test_input_action_and_scenario_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            game_dir = Path(directory)
            scenario = game_dir / "scenario.json"
            scenario.write_text("{}", encoding="utf-8")
            argv = [
                "CodolNaturalMatchTrace.py",
                "--game-dir",
                str(game_dir),
                "--input-action",
                "forward",
                "--input-scenario",
                str(scenario),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch(
                    "CodolNaturalMatchTrace.CodolGame.find_game_directory",
                    return_value=game_dir,
                ),
                patch.object(sys, "stderr", io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                parse_args()

    def test_retained_server_watcher_requires_retained_game(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            game_dir = Path(directory)
            argv = [
                "CodolNaturalMatchTrace.py",
                "--game-dir",
                str(game_dir),
                "--keep-server-watcher-running",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch(
                    "CodolNaturalMatchTrace.CodolGame.find_game_directory",
                    return_value=game_dir,
                ),
                patch.object(sys, "stderr", io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                parse_args()

    def test_input_parser_boundary_allows_one_frame_in_flight_at_detach(self) -> None:
        complete = {
            "server_message_enter_count": 80,
            "server_message_leave_count": 80,
            "packet_event_leave_count": 80,
            "accepted_packet_count": 80,
        }
        self.assertTrue(input_parser_boundary_complete(complete))
        self.assertTrue(
            input_parser_boundary_complete(
                {**complete, "server_message_enter_count": 81}
            )
        )
        self.assertFalse(
            input_parser_boundary_complete(
                {**complete, "server_message_enter_count": 82}
            )
        )
        self.assertFalse(
            input_parser_boundary_complete(
                {**complete, "server_message_leave_count": 0}
            )
        )

    @unittest.skipUnless(shutil.which("node"), "node is required for generated JS syntax check")
    def test_match_flow_generated_javascript_parses(self) -> None:
        args = argparse.Namespace(
            action="frontend",
            mode="",
            map="",
            playlist_id=26,
            max_player=6,
            match_type=1,
            character_index=None,
            frontend_stable_seconds=0.0,
            force_client_allocation=False,
            skip_intro=True,
        )
        source = f"(function(){{\n{build_match_script(args, 1)}\n}})();\n"
        completed = subprocess.run(
            ["node", "--check", "-"],
            input=source,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_match_flow_does_not_reenter_native_match_or_ready_calls(self) -> None:
        args = argparse.Namespace(
            action="full",
            mode="",
            map="",
            playlist_id=26,
            max_player=6,
            match_type=1,
            character_index=None,
            frontend_stable_seconds=0.0,
            force_client_allocation=False,
            skip_intro=True,
        )
        source = build_match_script(args, 1)
        self.assertEqual(source.count("invokeQuickMatch(state);"), 1)
        self.assertIn("readyAttempts === 0", source)
        self.assertNotIn("lastMatchAttempt", source)
        self.assertIn("driveNow - lastDriveAt < 100", source)

    def test_match_flow_recovers_only_the_known_stalled_profile_state(self) -> None:
        args = argparse.Namespace(
            action="frontend",
            mode="",
            map="",
            playlist_id=26,
            max_player=6,
            match_type=1,
            character_index=None,
            frontend_stable_seconds=0.0,
            force_client_allocation=False,
            skip_intro=True,
        )
        source = build_match_script(args, 1)
        self.assertIn("profile.operation === 1", source)
        self.assertIn("profile.chunk_mask === '0x0'", source)
        self.assertIn("now - stalledProfileSince < 10000", source)
        self.assertIn("CODOL_RequestInventoryRefresh", source)
        self.assertIn("profileRecoveryAttempted = true", source)

    def test_forced_allocation_runs_in_the_ready_confirmation_drive(self) -> None:
        args = argparse.Namespace(
            action="full",
            mode="",
            map="",
            playlist_id=26,
            max_player=6,
            match_type=1,
            character_index=None,
            frontend_stable_seconds=0.0,
            force_client_allocation=True,
            skip_intro=True,
        )
        source = build_match_script(args, 1)
        ready_branch = source[source.index("type: 'ready_confirmed'") :]
        self.assertIn("invokeForcedAllocation();", ready_branch)
        forced_helper = source[
            source.index("function invokeForcedAllocation()") :
            source.index("Interceptor.attach(startGameAddress")
        ]
        self.assertIn("startGame(room, 1, -1, 0);", forced_helper)
        self.assertIn("observation: 'native_call_returned'", forced_helper)

    def test_match_flow_embeds_target_character_selection(self) -> None:
        args = argparse.Namespace(
            action="full",
            mode="",
            map="",
            playlist_id=26,
            max_player=6,
            match_type=1,
            character_index=2,
            frontend_stable_seconds=0.0,
            force_client_allocation=False,
            skip_intro=True,
        )
        source = build_match_script(args, 1)
        self.assertEqual(CURRENT_CHARACTER_SELECT_ITEM_RVA, 0x289FF0)
        self.assertIn("const targetCharacterIndex = 2;", source)
        self.assertIn("characterSlotGet(targetCharacterIndex, 0)", source)
        self.assertIn("currentCharacterSelectItem(targetCharacterItemId);", source)
        self.assertIn("0x8B, 0x7C, 0x24, 0x08", source)
        self.assertIn("selector_target: currentCharacterSelectItemAddress.toString()", source)
        self.assertNotIn("currentCharacterEquip", source)
        self.assertNotIn("0x28C580", source)
        self.assertLess(
            source.index("state.current_character_index !== targetCharacterIndex"),
            source.index("refusing to change character while a room is active"),
        )
        self.assertIn("publicProfileUploadPoll();", source)
        self.assertIn("state.public_profile.dirty_flags === 0", source)
        self.assertNotIn("currentCharacterCache.writeS32", source)
        self.assertIn("source: 'client-native-forced'", source)

    def test_natural_match_propagates_target_character_to_both_native_probes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.character_index = 2
            flow = NaturalMatchTrace(args)
            flow.client_pid = 123
            process = MagicMock()
            with patch.object(flow, "start_process", return_value=process) as start:
                self.assertIs(flow.start_frontend_probe(5.0), process)
                frontend_command = start.call_args.args[1]
                self.assertEqual(frontend_command[-2:], ["--character-index", "2"])

                self.assertIs(flow.start_match({"active": False}), process)
                match_command = start.call_args.args[1]
                self.assertEqual(match_command[-2:], ["--character-index", "2"])

    def test_probe_commands_route_to_their_owning_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            flow.client_pid = 123
            flow.dedicated_pid = 456
            process = MagicMock()
            with patch.object(flow, "start_process", return_value=process) as start:
                flow.start_frontend_probe(5.0)
                frontend_command = start.call_args.args[1]
                flow.start_tracer()
                tracer_command = start.call_args.args[1]
                flow.start_server_watcher()
                server_command = start.call_args.args[1]
                flow.start_match({"active": False})
                match_command = start.call_args.args[1]

            for command in (frontend_command, tracer_command, match_command):
                self.assertEqual(command[command.index("--pid") + 1], "123")
            self.assertEqual(server_command[server_command.index("--pid") + 1], "456")

    def test_server_watcher_tracks_each_requested_damage_entity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.watch_damage_entity_num = [273, 274]
            flow = NaturalMatchTrace(args)
            flow.dedicated_pid = 456
            process = MagicMock()
            with patch.object(flow, "start_process", return_value=process) as start:
                self.assertIs(flow.start_server_watcher(), process)

            command = start.call_args.args[1]
            self.assertEqual(
                [
                    command[index + 1]
                    for index, value in enumerate(command)
                    if value == "--damage-entity-num"
                ],
                ["273", "274"],
            )

    def test_summary_checkpoint_retries_windows_reader_contention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            original_replace = Path.replace
            attempts = 0

            def flaky_replace(source: Path, target: Path) -> Path:
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise PermissionError("checkpoint is briefly open by a reader")
                return original_replace(source, target)

            with (
                patch.object(Path, "replace", flaky_replace),
                patch("CodolNaturalMatchTrace.time.sleep"),
            ):
                flow.write_summary_checkpoint()

            self.assertEqual(attempts, 2)
            self.assertTrue(flow.summary_path.is_file())

    def test_progress_survives_a_closed_stdout_pipe(self) -> None:
        class ClosedPipe:
            def write(self, _value: str) -> int:
                raise OSError(22, "stdout pipe is closed")

            def flush(self) -> None:
                raise OSError(22, "stdout pipe is closed")

        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            with patch.object(sys, "stdout", ClosedPipe()):
                flow.emit_progress("waiting_frontend", force=True)

            self.assertEqual(flow.summary["current_phase"], "waiting_frontend")
            self.assertIn(
                "progress stdout unavailable; continuing with summary checkpoint",
                flow.summary["warnings"],
            )

    def test_input_exercise_gates_raw_integrity_without_gameplay_heuristics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.input_action = "jump"
            flow = NaturalMatchTrace(args)
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            scenario = single_action_scenario("jump", 0.1, 0.2)
            payload = complete_input_capture_payload(
                flow.output / "client_input.json", scenario
            )
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload), stderr=""
            )
            with (
                patch.object(flow, "stop_server_watcher") as stop_server,
                patch.object(flow, "stop_tracer") as stop_tracer,
                patch.object(flow, "run_command", return_value=completed) as run_command,
            ):
                flow.exercise_client_input()

            stop_server.assert_not_called()
            stop_tracer.assert_not_called()
            command = run_command.call_args.args[1]
            self.assertIn("--output", command)
            input_timeout = float(command[command.index("--timeout") + 1])
            process_timeout = run_command.call_args.args[2]
            self.assertGreaterEqual(
                process_timeout,
                input_timeout + 4.0,
            )
            self.assertEqual(flow.summary["client_input"]["evidence_level"], "client-native-forced")
            self.assertEqual(
                flow.summary["client_input"]["parent_validation"],
                {
                    "raw_capture_integrity": True,
                    "gameplay_conformance_evaluated": False,
                },
            )
            raw_path = (flow.output / "client_input.samples.jsonl").resolve()
            blob_path = (flow.output / "client_input.samples.bin").resolve()
            self.assertTrue(raw_path.is_file())
            self.assertEqual(blob_path.read_bytes(), b"opaque-evidence")
            self.assertNotIn("pmove_capture", flow.summary["client_input"])
            self.assertEqual(list(flow.output.glob("*.pmt")), [])

    def test_input_exercise_keeps_frame_trace_alive_through_probe_startup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.input_action = "jump"
            args.frame_trace = True
            flow = NaturalMatchTrace(args)
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            scenario = single_action_scenario("jump", 0.1, 0.2)
            payload = complete_input_capture_payload(
                flow.output / "client_input.json", scenario
            )
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload), stderr=""
            )
            with (
                patch.object(flow, "stop_server_watcher"),
                patch.object(flow, "start_input_frame_trace") as start_frame_trace,
                patch.object(flow, "finish_input_frame_trace") as finish_frame_trace,
                patch.object(flow, "run_command", return_value=completed),
            ):
                flow.exercise_client_input()

            self.assertAlmostEqual(start_frame_trace.call_args.args[0], 5.3)
            finish_frame_trace.assert_called_once_with()

    def test_input_exercise_rejects_terminal_history_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.input_action = "jump"
            flow = NaturalMatchTrace(args)
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            scenario = single_action_scenario("jump", 0.1, 0.2)
            payload = complete_input_capture_payload(
                flow.output / "client_input.json", scenario
            )
            payload["events"][-1]["event"] = "aborted"
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload), stderr=""
            )
            with (
                patch.object(flow, "stop_server_watcher"),
                patch.object(flow, "run_command", return_value=completed),
                self.assertRaisesRegex(
                    ProtocolFailure, "terminal event history"
                ),
            ):
                flow.exercise_client_input()

    def test_input_exercise_rejects_same_size_raw_blob_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.input_action = "jump"
            flow = NaturalMatchTrace(args)
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            scenario = single_action_scenario("jump", 0.1, 0.2)
            payload = complete_input_capture_payload(
                flow.output / "client_input.json", scenario
            )
            blob_path = flow.output / "client_input.samples.bin"
            blob_path.write_bytes(b"x" * blob_path.stat().st_size)
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload), stderr=""
            )
            with (
                patch.object(flow, "stop_server_watcher"),
                patch.object(flow, "run_command", return_value=completed),
                self.assertRaisesRegex(ProtocolFailure, "independent validation"),
            ):
                flow.exercise_client_input()

    def test_input_scenario_freezes_sha_and_requires_capture_integrity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario = root / "scenario.json"
            scenario.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "name": "movement-window",
                        "events": [
                            {"at_ms": 500, "action": "forward", "transition": "down"},
                            {"at_ms": 750, "action": "forward", "transition": "up"},
                        ],
                        "observe_after_ms": 250,
                    }
                ),
                encoding="utf-8",
            )
            args = test_args(root / "run")
            args.input_scenario = scenario
            args.input_scenario_payload = load_scenario(scenario)
            scenario.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "name": "mutated-after-parent-parse",
                        "events": [
                            {"at_ms": 0, "action": "weapnext", "transition": "activate"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            flow = NaturalMatchTrace(args)
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            self.assertIsNotNone(flow.freeze_input_scenario())
            scenario_sha256 = flow.summary["input_scenario"]["sha256"]
            payload = complete_input_capture_payload(
                flow.output / "client_input.json",
                args.input_scenario_payload,
                scenario_sha256=scenario_sha256,
            )
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload), stderr=""
            )
            with (
                patch.object(flow, "stop_server_watcher") as stop_server,
                patch.object(flow, "run_command", return_value=completed) as run_command,
            ):
                flow.exercise_client_input()

            stop_server.assert_not_called()
            command = run_command.call_args.args[1]
            self.assertIn("--scenario", command)
            snapshot_path = Path(command[command.index("--scenario") + 1])
            self.assertEqual(snapshot_path, flow.input_scenario_snapshot_path)
            self.assertNotEqual(snapshot_path, scenario)
            self.assertEqual(
                command[command.index("--scenario-sha256") + 1],
                scenario_sha256,
            )
            snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot_payload["name"], "movement-window")
            snapshot_bytes = snapshot_path.read_bytes()
            self.assertEqual(
                flow.summary["input_scenario"]["sha256"],
                hashlib.sha256(snapshot_bytes).hexdigest(),
            )
            self.assertEqual(
                flow.summary["input_scenario"]["source_path"],
                str(scenario.resolve()),
            )
            self.assertNotIn("--hold-seconds", command)
            input_timeout = float(command[command.index("--timeout") + 1])
            self.assertAlmostEqual(input_timeout, 9.0)
            self.assertAlmostEqual(run_command.call_args.args[2], 13.0)
            self.assertEqual(
                flow.summary["client_input"]["evidence_level"],
                "client-native-forced",
            )
            self.assertEqual(
                hashlib.sha256(snapshot_path.read_bytes()).hexdigest(), scenario_sha256
            )

    def test_input_scenario_rejects_snapshot_mutation_during_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario = root / "scenario.json"
            scenario.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "name": "missing-world",
                        "events": [
                            {"at_ms": 100, "action": "forward", "transition": "down"},
                            {"at_ms": 200, "action": "forward", "transition": "up"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = test_args(root / "run")
            args.input_scenario = scenario
            flow = NaturalMatchTrace(args)
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            self.assertIsNotNone(flow.freeze_input_scenario())
            assert flow.input_scenario_snapshot is not None
            payload = complete_input_capture_payload(
                flow.output / "client_input.json",
                flow.input_scenario_snapshot,
                scenario_sha256=flow.summary["input_scenario"]["sha256"],
            )
            assert flow.input_scenario_snapshot_path is not None
            flow.input_scenario_snapshot_path.write_text(
                json.dumps(single_action_scenario("back", 0.1, 0.2)),
                encoding="utf-8",
            )
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload), stderr=""
            )
            with (
                patch.object(flow, "stop_server_watcher"),
                patch.object(flow, "run_command", return_value=completed),
                self.assertRaisesRegex(ProtocolFailure, "frozen input scenario changed"),
            ):
                flow.exercise_client_input()

    def test_viewmodel_trace_arms_before_capture_and_records_diagnosis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.viewmodel_trace = True
            args.viewmodel_trace_seconds = 0.0
            flow = NaturalMatchTrace(args)
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            payload = {
                "ok": True,
                "counts": {"add_view_weapon": 20},
                "diagnosis": {"result": "viewmodel_dobj_missing"},
            }
            managed = fake_process(flow.output, "viewmodel_trace")

            def start_viewmodel(*_args: Any, **_kwargs: Any) -> ManagedProcess:
                flow.viewmodel_ready_path.write_text(
                    json.dumps({"ready": True, "pid": 123}), encoding="utf-8"
                )
                return managed

            with (
                patch.object(flow, "stop_tracer") as stop_tracer,
                patch.object(flow, "start_process", side_effect=start_viewmodel) as start_process,
            ):
                flow.arm_viewmodel_trace()

            stop_tracer.assert_called_once()
            self.assertIn("--ready-file", start_process.call_args.args[1])
            self.assertNotIn("stop_server_watch", start_process.call_args.args[1])

            flow.viewmodel_trace_path.write_text(json.dumps(payload), encoding="utf-8")
            flow.finish_viewmodel_trace()
            self.assertEqual(
                flow.summary["viewmodel_trace"]["diagnosis"]["result"],
                "viewmodel_dobj_missing",
            )

    def test_netchan_tracer_owns_the_cbuf_stream_in_the_same_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            tracer = fake_process(flow.output, "tracer")
            with patch.object(flow, "start_process", return_value=tracer) as start_process:
                self.assertIs(flow.start_tracer(), tracer)

            name, command = start_process.call_args.args
            self.assertEqual(name, "netchan_tracer")
            self.assertEqual(command.count("--cbuf-log"), 1)
            self.assertEqual(
                command[command.index("--cbuf-log") + 1],
                str(flow.cbuf_trace_path),
            )
            tracer.close_streams()

    def test_forced_allocation_source_requires_explicit_opt_in(self) -> None:
        self.assertTrue(allocation_source_allowed(False, "client-native"))
        self.assertTrue(allocation_source_allowed(True, "client-native"))
        self.assertTrue(allocation_source_allowed(True, "frida-forced"))
        self.assertFalse(allocation_source_allowed(False, "frida-forced"))
        self.assertFalse(allocation_source_allowed(True, "synthetic"))

    def test_active_world_reuse_requires_client_server_and_parser_boundary(self) -> None:
        frontend_state = {
            "connection_state": 10,
            "active": True,
            "player_count": 1,
        }
        sample = {
            "payload": {
                "ok": True,
                "after": {
                    "active_clients": 1,
                    "gamestate_updates_received": 1,
                    "gamestate_messages_sent": 1,
                    "snapshot_messages_sent": 10,
                    "world_spawn_configured": True,
                },
            }
        }
        events = [
            {"event": "parse_snapshot_enter"},
            {"event": "parse_playerstate_enter"},
            {"event": "parse_playerstate_leave", "overflowed": 0},
            {"event": "parse_snapshot_leave", "overflowed": 0},
        ]

        self.assertTrue(active_world_reusable(frontend_state, sample, events))
        self.assertFalse(
            active_world_reusable({**frontend_state, "connection_state": 1}, sample, events)
        )
        self.assertFalse(
            active_world_reusable(frontend_state, sample, events[:-1])
        )

    def test_active_world_reuse_marks_top_level_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            flow.output.mkdir(parents=True)
            flow.tracer = fake_process(flow.output, "tracer")
            flow.server_watcher = fake_process(flow.output, "server")
            frontend_state = {
                "connection_state": 10,
                "active": True,
                "player_count": 1,
            }
            sample = {
                "payload": {
                    "ok": True,
                    "after": {
                        "active_clients": 1,
                        "gamestate_updates_received": 1,
                        "gamestate_messages_sent": 1,
                        "snapshot_messages_sent": 10,
                        "world_spawn_configured": True,
                    },
                }
            }
            events = [
                {"event": "parse_snapshot_enter"},
                {"event": "parse_playerstate_enter"},
                {"event": "parse_playerstate_leave", "overflowed": 0},
                {"event": "parse_snapshot_leave", "overflowed": 0},
            ]
            flow.server_samples_path.write_text(
                json.dumps(sample) + "\n", encoding="utf-8"
            )
            flow.trace_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            with patch.object(flow, "monitor_world_boundary"):
                self.assertTrue(flow.reuse_active_world(frontend_state))

            self.assertEqual(flow.summary["evidence_level"], "existing-active-world")
            self.assertEqual(
                flow.summary["world_reuse"]["evidence_level"],
                "existing-active-world",
            )
            flow.tracer.close_streams()
            flow.server_watcher.close_streams()

    def test_fast_regression_mode_never_starts_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.require_active_world = True
            flow = NaturalMatchTrace(args)
            with (
                patch.object(flow, "reuse_active_world", return_value=False),
                patch.object(flow, "start_match") as start_match,
                self.assertRaisesRegex(ProtocolFailure, "will not start QuickMatch"),
            ):
                flow.acquire_world({"connection_state": 0})

            start_match.assert_not_called()

    def test_fast_regression_mode_never_launches_game(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.game_dir = Path(directory)
            args.require_active_world = True
            flow = NaturalMatchTrace(args)
            with (
                patch("CodolNaturalMatchTrace.CodolGame.running_pids", return_value=[]),
                patch.object(flow, "run_command") as run_command,
                self.assertRaisesRegex(ProtocolFailure, "will not launch or repair"),
            ):
                flow.prepare_game()

            run_command.assert_not_called()

    def test_prepare_game_reuses_one_tracked_client_and_dedicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.game_dir = Path(directory)
            flow = NaturalMatchTrace(args)

            def role_pids(_game_dir: Path, role: str) -> list[int]:
                return [123] if role == "client" else [456]

            with (
                patch(
                    "CodolNaturalMatchTrace.CodolGame.running_pids",
                    return_value=[123, 456],
                ),
                patch(
                    "CodolNaturalMatchTrace.CodolGame.role_pids",
                    side_effect=role_pids,
                ),
                patch.object(flow, "run_command") as run_command,
            ):
                self.assertEqual(flow.prepare_game(), (123, 456))

            run_command.assert_not_called()

    def test_prepare_game_launches_a_dedicated_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.game_dir = Path(directory)
            flow = NaturalMatchTrace(args)
            with (
                patch(
                    "CodolNaturalMatchTrace.CodolGame.running_pids",
                    side_effect=([], [123, 456]),
                ),
                patch(
                    "CodolNaturalMatchTrace.CodolGame.role_pids",
                    side_effect=([], [], [123], [456]),
                ),
                patch.object(flow, "run_command") as run_command,
            ):
                self.assertEqual(flow.prepare_game(), (123, 456))

            name, command = run_command.call_args.args[:2]
            self.assertEqual(name, "launch_dedicated_pair")
            self.assertIn("launch-dedicated", command)
            self.assertTrue(flow.started_game)

    def test_match_command_can_request_client_native_forced_allocation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.force_client_allocation = True
            flow = NaturalMatchTrace(args)
            flow.client_pid = 123
            with patch.object(flow, "start_process") as start_process:
                flow.start_match({"active": False})

            command = start_process.call_args.args[1]
            self.assertIn("--force-client-allocation", command)

    def test_match_command_resumes_an_existing_unready_room(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            flow.client_pid = 123
            state = {
                "active": True,
                "player_count": 1,
                "ready": 0,
                "quick_match_ready": True,
            }
            with patch.object(flow, "start_process") as start_process:
                flow.start_match(state)

            command = start_process.call_args.args[1]
            self.assertEqual(command[command.index("--action") + 1], "resume")
            self.assertEqual(flow.match_trigger_state, state)

    def test_progress_checkpoint_is_flushed_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            flow.output.mkdir(parents=True)
            with patch("builtins.print") as output:
                flow.emit_progress(
                    "waiting_allocation",
                    force=True,
                    elapsed_seconds=12.5,
                )

            checkpoint = json.loads(flow.summary_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["outcome"], "running")
            self.assertEqual(checkpoint["current_phase"], "waiting_allocation")
            self.assertEqual(checkpoint["progress"]["elapsed_seconds"], 12.5)
            output.assert_called_once()
            self.assertTrue(output.call_args.kwargs["flush"])

    def test_frontend_wait_uses_native_quick_match_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            probe = fake_process(flow.output, "frontend")
            state = {
                "active": False,
                "connection_state": 1,
                "cinematic_active": False,
                "lobby_logged_on": True,
                "public_profile_ready": True,
                "quick_match_ready": True,
                "quick_match_dependencies": {
                    "primary_config": {"readable": True},
                    "secondary_config": {"readable": True},
                    "room_service": {"readable": True},
                },
            }
            probe.stdout_stream.write(
                json.dumps({"type": "frontend_ready", "stable_seconds": 2.0, "state": state})
                + "\n"
            )
            probe.stdout_stream.flush()
            probe.process.poll.return_value = 0
            probe.process.returncode = 0
            with (
                patch.object(flow, "start_frontend_probe", return_value=probe),
                patch.object(flow, "frontend_marker", return_value="existing process"),
            ):
                result = flow.wait_for_frontend()

            self.assertEqual(result, state)
            self.assertEqual(
                flow.summary["frontend_probe"]["source"],
                "codol-native-quick-match-state",
            )

    def test_frontend_readiness_rejects_partial_dependencies(self) -> None:
        state = {
            "active": False,
            "connection_state": 1,
            "cinematic_active": False,
            "lobby_logged_on": True,
            "public_profile_ready": True,
            "quick_match_ready": True,
            "quick_match_dependencies": {
                "primary_config": {"readable": True},
                "room_service": {"readable": False},
            },
        }
        self.assertFalse(quick_match_frontend_ready(state))

    def test_frontend_readiness_uses_lobby_profile_and_cinematic_state(self) -> None:
        state = {
            "active": False,
            "connection_state": 0,
            "cinematic_active": False,
            "lobby_logged_on": True,
            "public_profile_ready": True,
            "quick_match_ready": True,
            "quick_match_dependencies": {
                "primary_config": {"readable": True},
                "secondary_config": {"readable": True},
                "room": {"readable": True, "methods_ready": True},
                "room_service": {"readable": True, "methods_ready": True},
                "match_callbacks": {"readable": True},
                "match_list_primary": {"readable": True},
                "match_list_secondary": {"readable": True},
            },
        }
        self.assertTrue(quick_match_frontend_ready(state))

    def test_frontend_readiness_rejects_startup_cinematic(self) -> None:
        state = {
            "active": False,
            "cinematic_active": True,
            "lobby_logged_on": True,
            "public_profile_ready": True,
            "quick_match_ready": True,
            "quick_match_dependencies": {
                "room": {"readable": True, "methods_ready": True},
            },
        }
        self.assertFalse(quick_match_frontend_ready(state))

    def test_frontend_readiness_rejects_incomplete_profile(self) -> None:
        state = {
            "active": False,
            "cinematic_active": False,
            "lobby_logged_on": True,
            "public_profile_ready": False,
            "quick_match_ready": True,
            "quick_match_dependencies": {
                "room": {"readable": True, "methods_ready": True},
            },
        }
        self.assertFalse(quick_match_frontend_ready(state))

    def test_frontend_readiness_accepts_an_existing_room_for_resume(self) -> None:
        state = {
            "active": True,
            "player_count": 1,
            "ready": 0,
            "quick_match_ready": True,
            "quick_match_dependencies": {
                "room": {"readable": True, "methods_ready": True},
                "room_service": {"readable": True, "methods_ready": True},
            },
        }
        self.assertTrue(quick_match_frontend_ready(state))

    def test_frontend_readiness_rejects_an_empty_active_room(self) -> None:
        state = {
            "active": True,
            "player_count": 0,
            "ready": 0,
            "quick_match_ready": True,
            "quick_match_dependencies": {
                "room": {"readable": True, "methods_ready": True},
                "room_service": {"readable": True, "methods_ready": True},
            },
        }
        self.assertFalse(quick_match_frontend_ready(state))

    def test_clean_launch_waits_for_telemetry_before_native_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            flow.output.mkdir(parents=True)
            flow.client_pid = 123
            flow.started_game = True
            probe = fake_process(flow.output, "frontend")
            state = {
                "active": False,
                "connection_state": 1,
                "cinematic_active": False,
                "lobby_logged_on": True,
                "public_profile_ready": True,
                "quick_match_ready": True,
                "quick_match_dependencies": {
                    "primary_config": {"readable": True},
                    "secondary_config": {"readable": True},
                    "room_service": {"readable": True},
                },
            }
            probe.stdout_stream.write(
                json.dumps({"type": "frontend_ready", "stable_seconds": 0.1, "state": state})
                + "\n"
            )
            probe.stdout_stream.flush()
            probe.process.poll.return_value = 0
            probe.process.returncode = 0
            with (
                patch("CodolNaturalMatchTrace.CodolGame.running_pids", return_value=[123]),
                patch("CodolNaturalMatchTrace.time.sleep"),
                patch.object(flow, "frontend_marker", side_effect=(None, "marker", "marker")),
                patch.object(flow, "start_frontend_probe", return_value=probe) as start_probe,
            ):
                self.assertEqual(flow.wait_for_frontend(), state)

            start_probe.assert_called_once()
            self.assertEqual(flow.summary["frontend_probe"]["client_load_time_marker"], "marker")

    def test_match_never_starts_when_watcher_is_not_armed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            tracer: ManagedProcess | None = None

            def start_tracer() -> ManagedProcess:
                nonlocal tracer
                tracer = fake_process(flow.output, "tracer")
                return tracer

            with (
                patch.object(flow, "prepare_game", return_value=(123, 456)),
                patch.object(flow, "wait_for_frontend", return_value={}),
                patch.object(flow, "start_tracer", side_effect=start_tracer),
                patch.object(flow, "wait_for_trace_ready", side_effect=WorkflowTimeout("not armed")),
                patch.object(flow, "start_match") as start_match,
                patch.object(flow, "stop_tracer") as stop_tracer,
            ):
                self.assertEqual(flow.run(), 2)

            start_match.assert_not_called()
            stop_tracer.assert_called_once()
            summary = json.loads(flow.summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["outcome"], "timeout")
            if tracer is not None:
                tracer.close_streams()

    def test_tracer_stops_after_subprocess_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))

            def start_tracer() -> ManagedProcess:
                return fake_process(flow.output, "tracer")

            def start_match(_frontend_state: dict[str, Any]) -> ManagedProcess:
                return fake_process(flow.output, "match")

            def start_server_watcher() -> ManagedProcess:
                return fake_process(flow.output, "server")

            with (
                patch.object(flow, "prepare_game", return_value=(123, 456)),
                patch.object(flow, "wait_for_frontend", return_value={}),
                patch.object(flow, "start_tracer", side_effect=start_tracer),
                patch.object(flow, "wait_for_trace_ready"),
                patch.object(flow, "start_server_watcher", side_effect=start_server_watcher),
                patch.object(flow, "wait_for_server_watch_ready"),
                patch.object(flow, "start_match", side_effect=start_match),
                patch.object(flow, "monitor_match", side_effect=CommandFailure("match failed")),
                patch.object(flow, "stop_process") as stop_process,
                patch.object(flow, "stop_tracer") as stop_tracer,
                patch.object(flow, "stop_server_watcher") as stop_server_watcher,
            ):
                self.assertEqual(flow.run(), 2)

            stop_process.assert_called_once()
            stop_tracer.assert_called_once()
            stop_server_watcher.assert_called_once()
            summary = json.loads(flow.summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["outcome"], "subprocess_failure")
            flow.tracer.close_streams()
            flow.server_watcher.close_streams()
            flow.match.close_streams()

    def test_summary_classifies_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            with (
                patch.object(flow, "prepare_game", return_value=(123, 456)),
                patch.object(flow, "wait_for_frontend", return_value={}),
                patch.object(flow, "start_tracer", side_effect=lambda: fake_process(flow.output, "tracer")),
                patch.object(flow, "wait_for_trace_ready"),
                patch.object(
                    flow,
                    "start_server_watcher",
                    side_effect=lambda: fake_process(flow.output, "server"),
                ),
                patch.object(flow, "wait_for_server_watch_ready"),
                patch.object(
                    flow,
                    "start_match",
                    side_effect=lambda _state: fake_process(flow.output, "match"),
                ),
                patch.object(flow, "monitor_match"),
                patch.object(flow, "dispatch_forced_reliable_command"),
                patch.object(flow, "capture_window"),
                patch.object(flow, "capture_cgame_state"),
                patch.object(flow, "stop_tracer"),
                patch.object(flow, "stop_server_watcher"),
            ):
                self.assertEqual(flow.run(), 0)

            summary = json.loads(flow.summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["outcome"], "success")
            flow.tracer.close_streams()
            flow.server_watcher.close_streams()
            flow.match.close_streams()

    def test_success_can_retain_server_watcher_for_live_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.keep_server_watcher_running = True
            flow = NaturalMatchTrace(args)
            server_watcher: ManagedProcess | None = None

            def start_server_watcher() -> ManagedProcess:
                nonlocal server_watcher
                server_watcher = fake_process(flow.output, "server")
                server_watcher.process.pid = 789
                return server_watcher

            with (
                patch.object(flow, "prepare_game", return_value=(123, 456)),
                patch.object(flow, "wait_for_frontend", return_value={}),
                patch.object(flow, "start_tracer", side_effect=lambda: fake_process(flow.output, "tracer")),
                patch.object(flow, "wait_for_trace_ready"),
                patch.object(flow, "start_server_watcher", side_effect=start_server_watcher),
                patch.object(flow, "wait_for_server_watch_ready"),
                patch.object(flow, "acquire_world"),
                patch.object(flow, "capture_window"),
                patch.object(flow, "capture_cgame_state"),
                patch.object(flow, "stop_tracer"),
                patch.object(flow, "stop_server_watcher") as stop_server_watcher,
            ):
                self.assertEqual(flow.run(), 0)

            stop_server_watcher.assert_not_called()
            summary = json.loads(flow.summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["retained_server_watcher"]["pid"], 789)
            self.assertEqual(
                summary["retained_server_watcher"]["log"],
                str(flow.server_samples_path),
            )
            self.assertEqual(
                summary["retained_server_watcher"]["stop_file"],
                str(flow.server_watch_stop_path),
            )
            flow.tracer.close_streams()
            if server_watcher is not None:
                server_watcher.close_streams()

    def test_forced_reliable_command_waits_for_server_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.forced_reliable_command = "cmd mr 0 1 custom1"
            flow = NaturalMatchTrace(args)
            flow.client_pid = 123
            completed = subprocess.CompletedProcess(
                [],
                0,
                stdout=json.dumps({"ok": True, "source": "frida-forced"}),
                stderr="",
            )
            sample = {
                "payload": {
                    "after": {
                        "client_ingress": [{
                            "last_reliable_command": {
                                "sequence": 4,
                                "command": "mr 0 1 custom1",
                            },
                            "last_menu_response": {
                                "sequence": 4,
                                "menu_name": "changeclass_marines",
                                "response": "custom1",
                            },
                            "gameplay": {
                                "name": "playing",
                                "selected_loadout": "custom1",
                            },
                        }]
                    }
                }
            }
            baseline = {
                "payload": {
                    "after": {
                        "client_ingress": [{
                            "last_reliable_command": {
                                "sequence": 3,
                                "command": "s",
                            },
                            "gameplay": {"name": "waiting_for_loadout"},
                        }]
                    }
                }
            }
            with (
                patch.object(flow, "run_command", return_value=completed) as run_command,
                patch("CodolNaturalMatchTrace.CodolGame.running_pids", return_value=[123]),
                patch(
                    "CodolNaturalMatchTrace.read_jsonl",
                    side_effect=([baseline], [sample]),
                ),
                patch.object(flow, "emit_progress"),
            ):
                flow.dispatch_forced_reliable_command()

            observed = flow.summary["forced_reliable_command"]
            self.assertEqual(observed["evidence_level"], "client-native-forced")
            self.assertEqual(observed["requested_command"], "cmd mr 0 1 custom1")
            self.assertEqual(observed["command"], "mr 0 1 custom1")
            self.assertEqual(observed["baseline_reliable_sequence"], 3)
            self.assertEqual(observed["observed"]["command"], "mr 0 1 custom1")
            self.assertEqual(observed["menu_response"]["menu_name"], "changeclass_marines")
            self.assertEqual(observed["gameplay"]["name"], "playing")
            self.assertEqual(run_command.call_args.args[1][-1], "cmd mr 0 1 custom1")

    def test_forced_menu_response_survives_later_reliable_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.forced_reliable_command = "mr 0 1 custom1"
            flow = NaturalMatchTrace(args)
            flow.client_pid = 123
            completed = subprocess.CompletedProcess(
                [], 0, stdout=json.dumps({"ok": True, "source": "frida-forced"}), stderr=""
            )
            baseline = {
                "payload": {
                    "after": {
                        "client_ingress": [{
                            "last_reliable_command": {"sequence": 4, "command": "s"},
                            "gameplay": {"name": "waiting_for_loadout"},
                        }]
                    }
                }
            }
            observed_sample = {
                "payload": {
                    "after": {
                        "client_ingress": [{
                            "last_reliable_command": {"sequence": 7, "command": "n 66"},
                            "last_menu_response": {
                                "sequence": 5,
                                "menu_name": "changeclass_marines",
                                "response": "custom1",
                            },
                            "gameplay": {
                                "name": "playing",
                                "selected_loadout": "custom1",
                            },
                        }]
                    }
                }
            }
            with (
                patch.object(flow, "run_command", return_value=completed),
                patch("CodolNaturalMatchTrace.CodolGame.running_pids", return_value=[123]),
                patch(
                    "CodolNaturalMatchTrace.read_jsonl",
                    side_effect=([baseline], [observed_sample]),
                ),
                patch.object(flow, "emit_progress"),
            ):
                flow.dispatch_forced_reliable_command()

            observed = flow.summary["forced_reliable_command"]
            self.assertEqual(observed["status"], "dispatched_and_observed")
            self.assertIsNone(observed["observed"])
            self.assertEqual(observed["menu_response"]["sequence"], 5)

    def test_forced_reliable_command_skips_an_already_selected_loadout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = test_args(Path(directory) / "run")
            args.forced_reliable_command = "mr 0 1 custom1"
            flow = NaturalMatchTrace(args)
            flow.client_pid = 123
            sample = {
                "payload": {
                    "after": {
                        "client_ingress": [{
                            "last_reliable_command": {
                                "sequence": 8,
                                "command": "mr 0 1 custom1",
                            },
                            "last_menu_response": {
                                "menu_name": "changeclass_marines",
                                "response": "custom1",
                            },
                            "gameplay": {
                                "name": "playing",
                                "selected_loadout": "custom1",
                            },
                        }]
                    }
                }
            }
            with (
                patch("CodolNaturalMatchTrace.read_jsonl", return_value=[sample]),
                patch.object(flow, "run_command") as run_command,
                patch.object(flow, "emit_progress"),
            ):
                flow.dispatch_forced_reliable_command()

            run_command.assert_not_called()
            observed = flow.summary["forced_reliable_command"]
            self.assertEqual(observed["status"], "already_satisfied")
            self.assertTrue(observed["dispatch_skipped"])
            self.assertNotIn("evidence_level", observed)

    def test_forced_command_target_and_reliable_sequence_are_strict(self) -> None:
        client = {
            "last_menu_response": {"response": "custom1"},
            "gameplay": {"name": "playing", "selected_loadout": "custom1"},
        }
        self.assertTrue(forced_command_target_satisfied("mr 0 1 custom1", client))
        self.assertFalse(forced_command_target_satisfied("mr 0 1 custom2", client))
        self.assertFalse(forced_command_target_satisfied("disconnect", client))
        self.assertFalse(reliable_sequence_advanced(8, 8))
        self.assertTrue(reliable_sequence_advanced(9, 8))
        self.assertTrue(reliable_sequence_advanced(0, 0xFFFFFFFF))

    def test_forced_reliable_command_normalizes_one_cbuf_cmd_prefix(self) -> None:
        self.assertEqual(normalize_reliable_command("mr 0 1 custom1"), "mr 0 1 custom1")
        self.assertEqual(normalize_reliable_command("cmd mr 0 1 custom1"), "mr 0 1 custom1")
        with self.assertRaises(ValueError):
            normalize_reliable_command("cmd ")
        with self.assertRaisesRegex(ValueError, "mr <serverId> <menuIndex>"):
            normalize_reliable_command("mr custom3")
        with self.assertRaisesRegex(ValueError, "mr <serverId> <menuIndex>"):
            normalize_reliable_command("mr current changeclass custom3")

    def test_forced_loadout_checks_prepared_character_mask(self) -> None:
        status = {
            "loadout_preparation": {
                "prepared": True,
                "prepared_character": 0,
                "registered_class_mask": 0x19,
            }
        }
        self.assertTrue(forced_loadout_available("mr 0 1 custom1", status))
        self.assertFalse(forced_loadout_available("mr 0 1 custom3", status))
        self.assertTrue(forced_loadout_available("mr 0 1 class4", status))
        self.assertIsNone(forced_loadout_available("disconnect", status))
        self.assertIsNone(
            forced_loadout_available(
                "mr 0 1 custom3", {"loadout_preparation": {"prepared": False}}
            )
        )

    def test_trace_ready_uses_cbuf_attached_marker_for_shared_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flow = NaturalMatchTrace(test_args(Path(directory) / "run"))
            flow.output.mkdir(parents=True)
            flow.tracer = fake_process(flow.output, "tracer")
            flow.trace_path.write_text('{"event":"ready"}\n', encoding="utf-8")
            flow.cbuf_trace_path.write_text(
                '{"event":"ready"}\n{"event":"attached"}\n',
                encoding="utf-8",
            )

            flow.wait_for_trace_ready()

            self.assertIn("trace_armed_at", flow.summary)
            self.assertIn("cbuf_trace_armed_at", flow.summary)
            flow.tracer.close_streams()

    def test_powershell_file_command_always_bypasses_policy(self) -> None:
        command = powershell_file_command(Path("Install.ps1"), "-Mode", "release")
        self.assertEqual(
            command[1:7],
            [
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "Install.ps1",
            ],
        )

    def test_json_parser_accepts_pretty_server_status(self) -> None:
        self.assertEqual(json_objects('{\n  "ok": true,\n  "pid": 123\n}\n'), [{"ok": True, "pid": 123}])

    def test_world_boundary_requires_server_client_ack_spawn_and_parser_completion(self) -> None:
        complete_trace = [
            {"event": "parse_snapshot_enter", "overflowed": 0},
            {"event": "parse_playerstate_enter", "overflowed": 0},
            {"event": "parse_playerstate_leave", "overflowed": 0},
            {"event": "parse_snapshot_leave", "overflowed": 0},
        ]
        incomplete = {
            "payload": {
                "ok": True,
                "after": {
                    "active_clients": 0,
                    "gamestate_updates_received": 0,
                    "gamestate_messages_sent": 1,
                    "snapshot_messages_sent": 0,
                    "world_spawn_configured": False,
                },
            }
        }
        complete = {
            "payload": {
                "ok": True,
                "after": {
                    "active_clients": 1,
                    "gamestate_updates_received": 6,
                    "gamestate_messages_sent": 1,
                    "snapshot_messages_sent": 1,
                    "world_spawn_configured": True,
                },
            }
        }
        self.assertFalse(world_boundary_reached(incomplete, complete_trace))
        self.assertFalse(world_boundary_reached(complete, complete_trace[:-1]))
        self.assertTrue(world_boundary_reached(complete, complete_trace))

    def test_parser_boundary_rejects_unpaired_or_overflowed_snapshots(self) -> None:
        unpaired = [
            {"event": "parse_snapshot_enter", "overflowed": 0},
            {"event": "parse_playerstate_enter", "overflowed": 0},
        ]
        overflowed = [
            *unpaired,
            {"event": "playerstate_delta_field_leave", "overflowed": 1},
        ]
        outer_cursor_finished = [
            *unpaired,
            {"event": "parse_server_message_leave", "overflowed": 1},
        ]
        self.assertFalse(parser_trace_status(unpaired)["complete"])
        self.assertEqual(parser_trace_status(outer_cursor_finished)["overflow_events"], 0)
        self.assertEqual(parser_trace_status(overflowed)["overflow_events"], 1)

    def test_protocol_progress_tracker_rejects_an_active_frozen_transport(self) -> None:
        def sample(accepted: int, outgoing: int, sent: int) -> dict[str, Any]:
            return {
                "payload": {
                    "after": {
                        "client_connection_state": 10,
                        "packets_sent": sent,
                        "client_ingress": [{
                            "accepted_packets": accepted,
                            "outgoing_sequence": outgoing,
                        }],
                    }
                }
            }

        tracker = ProtocolProgressTracker(10.0, 100.0)
        self.assertIsNone(tracker.observe(sample(1, 2, 3), 100.0))
        self.assertIsNone(tracker.observe(sample(2, 3, 4), 109.0))
        self.assertIsNone(tracker.observe(sample(2, 3, 4), 118.9))
        self.assertIsNotNone(tracker.observe(sample(2, 3, 4), 119.0))


if __name__ == "__main__":
    unittest.main()
