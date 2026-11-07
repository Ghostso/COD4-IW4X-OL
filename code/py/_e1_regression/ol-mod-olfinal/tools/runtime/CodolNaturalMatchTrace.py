#!/usr/bin/env python3
"""Run a fully armed natural CODOL match capture and preserve its outcome."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import CodolGame
from CodolCaptureEvidence import (
    summarize_raw_sample_checkpoint,
    write_json_atomic,
)
from CodolInputScenario import (
    ACTION_NAMES,
    load_scenario,
    normalize_scenario,
    scenario_duration_seconds,
    single_action_scenario,
)


FRAME_TRACE_RUNTIME_GRACE_SECONDS = 5.0


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CLIENT_LOAD_TIME_MARKER = "10436C69656E744C6F616454696D65"


class WorkflowTimeout(RuntimeError):
    """A workflow phase did not reach its required terminal state."""


class CommandFailure(RuntimeError):
    """A required subprocess failed or exited unexpectedly."""


class ProtocolFailure(RuntimeError):
    """The client rejected or failed to finish parsing the server protocol."""


class _ClosedOutputSink:
    encoding = "utf-8"

    @staticmethod
    def write(value: str) -> int:
        return len(value)

    @staticmethod
    def flush() -> None:
        pass


class ProtocolProgressTracker:
    def __init__(self, timeout_seconds: float, now: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.last_progress_at = now
        self.previous: tuple[int, int, int] | None = None

    def observe(self, sample: dict[str, Any], now: float) -> str | None:
        payload = sample.get("payload")
        after = payload.get("after") if isinstance(payload, dict) else None
        if not isinstance(after, dict) or after.get("client_connection_state", 0) < 9:
            return None
        ingress = after.get("client_ingress")
        client = ingress[0] if isinstance(ingress, list) and ingress else None
        if not isinstance(client, dict):
            return None
        current = (
            int(client.get("accepted_packets", 0)),
            int(client.get("outgoing_sequence", 0)),
            int(after.get("packets_sent", 0)),
        )
        if self.previous is None or any(
            value > previous for value, previous in zip(current, self.previous)
        ):
            self.previous = current
            self.last_progress_at = now
            return None
        self.previous = current
        if now - self.last_progress_at < self.timeout_seconds:
            return None
        return (
            "active gameplay transport made no accepted/send progress for "
            f"{self.timeout_seconds:g}s"
        )


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def powershell_file_command(script: Path, *arguments: str) -> list[str]:
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    powershell = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not powershell.is_file():
        powershell = Path(shutil.which("powershell.exe") or "powershell.exe")
    return [
        str(powershell),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *arguments,
    ]


def json_objects(text: str) -> list[dict[str, Any]]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, dict):
        return [value]

    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def quick_match_frontend_ready(state: Any) -> bool:
    if not isinstance(state, dict):
        return False
    dependencies = state.get("quick_match_dependencies")
    resumable_room = (
        state.get("active") is True
        and isinstance(state.get("player_count"), int)
        and state["player_count"] >= 1
    )
    late_frontend_ready = (
        state.get("active") is False
        and state.get("lobby_logged_on") is True
        and state.get("public_profile_ready") is True
        and state.get("cinematic_active") is False
    )
    return (
        (late_frontend_ready or resumable_room)
        and state.get("quick_match_ready") is True
        and isinstance(dependencies, dict)
        and bool(dependencies)
        and all(
            isinstance(dependency, dict) and dependency.get("readable") is True
            for dependency in dependencies.values()
        )
    )


def allocation_source_allowed(force_client_allocation: bool, source: object) -> bool:
    return source == "client-native" or (
        force_client_allocation and source == "frida-forced"
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return json_objects(path.read_text(encoding="utf-8", errors="replace"))


def latest_server_status(samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    for sample in reversed(samples):
        payload = sample.get("payload")
        after = payload.get("after") if isinstance(payload, dict) else None
        if isinstance(after, dict):
            return after
    return None


def latest_server_client(samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    after = latest_server_status(samples)
    if isinstance(after, dict):
        ingress = after.get("client_ingress") if isinstance(after, dict) else None
        client = ingress[0] if isinstance(ingress, list) and ingress else None
        if isinstance(client, dict):
            return client
    return None


def menu_response_target(command: str) -> str | None:
    parts = command.split()
    if len(parts) == 4 and parts[0] == "mr":
        return parts[3]
    return None


def forced_loadout_available(command: str, status: Any) -> bool | None:
    target = menu_response_target(command)
    if target is None or not isinstance(status, dict):
        return None
    if target.startswith("custom") and target[6:].isdigit():
        class_index = int(target[6:]) - 1
    elif target.startswith("class") and target[5:].isdigit():
        class_index = int(target[5:])
    else:
        return None
    preparation = status.get("loadout_preparation")
    if (
        not isinstance(preparation, dict)
        or preparation.get("prepared") is not True
        or not isinstance(preparation.get("registered_class_mask"), int)
        or not 0 <= class_index < 5
    ):
        return None
    return bool(preparation["registered_class_mask"] & (1 << class_index))


def normalize_reliable_command(command: str) -> str:
    normalized = command.strip()
    if normalized == "cmd":
        normalized = ""
    elif normalized.startswith("cmd "):
        normalized = normalized[4:].lstrip()
    if not normalized:
        raise ValueError("reliable command payload must be non-empty")
    parts = normalized.split()
    if parts[0] == "mr":
        if len(parts) != 4 or not parts[1].isdigit() or not parts[2].isdigit():
            raise ValueError(
                "menu response must use 'mr <serverId> <menuIndex> <response>'"
            )
    return normalized


def forced_command_target_satisfied(command: str, client: Any) -> bool:
    target = menu_response_target(command)
    if target is None or not isinstance(client, dict):
        return False
    gameplay = client.get("gameplay")
    menu_response = client.get("last_menu_response")
    return (
        isinstance(gameplay, dict)
        and gameplay.get("name") == "playing"
        and gameplay.get("selected_loadout") == target
        and isinstance(menu_response, dict)
        and menu_response.get("response") == target
    )


def reliable_sequence_advanced(current: Any, baseline: Any) -> bool:
    if not isinstance(current, int):
        return False
    if not isinstance(baseline, int):
        return True
    distance = (current - baseline) & 0xFFFFFFFF
    return 0 < distance < 0x80000000


def parser_trace_status(events: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot_enters = sum(row.get("event") == "parse_snapshot_enter" for row in events)
    snapshot_leaves = sum(row.get("event") == "parse_snapshot_leave" for row in events)
    playerstate_enters = sum(row.get("event") == "parse_playerstate_enter" for row in events)
    playerstate_leaves = sum(row.get("event") == "parse_playerstate_leave" for row in events)
    overflow_events = sum(
        row.get("event") != "parse_server_message_leave"
        and row.get("overflowed") not in (None, 0, False)
        for row in events
    )
    return {
        "parse_snapshot_enter": snapshot_enters,
        "parse_snapshot_leave": snapshot_leaves,
        "parse_playerstate_enter": playerstate_enters,
        "parse_playerstate_leave": playerstate_leaves,
        "overflow_events": overflow_events,
        "complete": (
            snapshot_enters >= 1
            and snapshot_enters == snapshot_leaves
            and playerstate_enters >= 1
            and playerstate_enters == playerstate_leaves
            and overflow_events == 0
        ),
    }


def input_parser_boundary_complete(parser: dict[str, Any]) -> bool:
    enters = parser.get("server_message_enter_count", 0)
    leaves = parser.get("server_message_leave_count", 0)
    if not isinstance(enters, int) or not isinstance(leaves, int):
        return False
    # Detaching the input probe can catch the next network frame after its
    # enter hook but before the matching leave hook. At least one earlier
    # packet must still have completed and been accepted without parser error.
    return (
        leaves > 0
        and leaves <= enters <= leaves + 1
        and parser.get("packet_event_leave_count", 0) > 0
        and parser.get("accepted_packet_count", 0) > 0
    )


def world_boundary_reached(
    sample: dict[str, Any], events: list[dict[str, Any]]
) -> bool:
    payload = sample.get("payload")
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return False
    after = payload.get("after")
    return (
        isinstance(after, dict)
        and after.get("active_clients", 0) >= 1
        and after.get("gamestate_updates_received", 0) >= 1
        and after.get("gamestate_messages_sent", 0) >= 1
        and after.get("snapshot_messages_sent", 0) >= 1
        and after.get("world_spawn_configured") is True
        and parser_trace_status(events)["complete"] is True
    )


def active_world_reusable(
    frontend_state: dict[str, Any],
    sample: dict[str, Any],
    events: list[dict[str, Any]],
) -> bool:
    return (
        frontend_state.get("connection_state") == 10
        and frontend_state.get("active") is True
        and isinstance(frontend_state.get("player_count"), int)
        and frontend_state["player_count"] >= 1
        and world_boundary_reached(sample, events)
    )


@dataclass
class ManagedProcess:
    process: subprocess.Popen[Any]
    stdout_path: Path
    stderr_path: Path
    stdout_stream: Any
    stderr_stream: Any

    def close_streams(self) -> None:
        for stream in (self.stdout_stream, self.stderr_stream):
            if stream is not None and not stream.closed:
                stream.close()


class NaturalMatchTrace:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.repository = Path(__file__).resolve().parents[2]
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output = (
            args.output_dir.resolve()
            if args.output_dir is not None
            else self.repository / ".runtime" / "natural-match" / stamp
        )
        self.trace_path = self.output / "netchan_trace.jsonl"
        self.cbuf_trace_path = self.output / "cbuf_commands.jsonl"
        self.trace_stop_path = self.output / "stop_netchan_trace"
        self.asset_trace_path = self.output / "dedicated_asset_trace.jsonl"
        self.asset_trace_stop_path = self.output / "stop_dedicated_asset_trace"
        self.server_samples_path = self.output / "server_samples.jsonl"
        self.server_watch_stop_path = self.output / "stop_server_watch"
        self.viewmodel_trace_path = self.output / "viewmodel_trace.json"
        self.viewmodel_ready_path = self.output / "viewmodel_trace.ready.json"
        self.viewmodel_stop_path = self.output / "stop_viewmodel_trace"
        self.frame_trace_path = self.output / "frame_trace.jsonl"
        self.frame_trace_summary_path = self.output / "frame_trace.summary.json"
        self.summary_path = self.output / "summary.json"
        self.input_scenario_snapshot_path = self.output / "input_scenario.snapshot.json"
        self.input_scenario_snapshot: dict[str, Any] | None = None
        self.tracer: ManagedProcess | None = None
        self.asset_tracer: ManagedProcess | None = None
        self.server_watcher: ManagedProcess | None = None
        self.viewmodel_probe: ManagedProcess | None = None
        self.frame_trace: ManagedProcess | None = None
        self.frontend_probe: ManagedProcess | None = None
        self.match: ManagedProcess | None = None
        self.match_action = "full"
        self.match_trigger_state: dict[str, Any] | None = None
        self.client_pid: int | None = None
        self.dedicated_pid: int | None = None
        self.started_game = False
        self.backend_log_path = args.game_dir.resolve() / "Ayria" / "Logs" / "AlwaysofflineRe.Localnet32.log"
        self.backend_log_offset: int | None = None
        self.backend_log_scan_offset: int | None = None
        self.frontend_marker_line: str | None = None
        self.summary: dict[str, Any] = {
            "schema_version": 1,
            "started_at": utc_now(),
            "outcome": "running",
            "current_phase": "initializing",
            "evidence_level": "natural",
            "commands": [],
            "phase_durations_seconds": {},
            "warnings": [],
        }
        self.last_progress_emit_at = 0.0
        self.last_progress_phase: str | None = None

    def freeze_input_scenario(self) -> tuple[dict[str, Any], Path] | None:
        source = getattr(self.args, "input_scenario", None)
        if source is None:
            return None
        if self.input_scenario_snapshot is not None:
            return self.input_scenario_snapshot, self.input_scenario_snapshot_path

        scenario = getattr(self.args, "input_scenario_payload", None)
        if not isinstance(scenario, dict):
            scenario = load_scenario(source)
        else:
            scenario = normalize_scenario(scenario)
        payload = (
            json.dumps(
                scenario,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        self.input_scenario_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        with self.input_scenario_snapshot_path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

        digest = hashlib.sha256(payload).hexdigest()
        self.input_scenario_snapshot = scenario
        self.summary["input_scenario"] = {
            "name": scenario["name"],
            "version": scenario["version"],
            "source_path": str(source.resolve()),
            "snapshot_path": str(self.input_scenario_snapshot_path),
            "sha256": digest,
            "size_bytes": len(payload),
        }
        self.write_summary_checkpoint()
        return scenario, self.input_scenario_snapshot_path

    def write_summary_checkpoint(self) -> None:
        write_json_atomic(self.summary_path, self.summary)

    def emit_progress(self, phase: str, *, force: bool = False, **details: Any) -> None:
        now = time.monotonic()
        if (
            not force
            and phase == self.last_progress_phase
            and now - self.last_progress_emit_at < self.args.progress_interval
        ):
            return
        event = {
            "event": "progress",
            "phase": phase,
            "time": utc_now(),
            **details,
        }
        self.summary["current_phase"] = phase
        self.summary["last_progress_at"] = event["time"]
        self.summary["progress"] = details
        self.write_summary_checkpoint()
        try:
            print(json.dumps(event, ensure_ascii=False), flush=True)
        except OSError:
            warning = "progress stdout unavailable; continuing with summary checkpoint"
            if warning not in self.summary["warnings"]:
                self.summary["warnings"].append(warning)
                self.write_summary_checkpoint()
            sys.stdout = _ClosedOutputSink()
        self.last_progress_emit_at = now
        self.last_progress_phase = phase

    def record_command(
        self,
        name: str,
        command: list[str],
        result: subprocess.CompletedProcess[str],
        started: float,
    ) -> None:
        self.summary["commands"].append(
            {
                "name": name,
                "command": command,
                "returncode": result.returncode,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            }
        )

    def run_command(
        self,
        name: str,
        command: list[str],
        timeout: float,
        required: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        started = time.monotonic()
        try:
            result = subprocess.run(
                command,
                cwd=self.repository,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=CREATE_NO_WINDOW,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            self.summary["commands"].append(
                {
                    "name": name,
                    "command": command,
                    "timed_out": True,
                    "timeout_seconds": timeout,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "stdout": (error.stdout or "")[-4000:],
                    "stderr": (error.stderr or "")[-4000:],
                }
            )
            raise
        self.record_command(name, command, result, started)
        if required and result.returncode != 0:
            raise CommandFailure(f"{name} exited with code {result.returncode}")
        return result

    def start_process(self, name: str, command: list[str]) -> ManagedProcess:
        stdout_path = self.output / f"{name}.stdout.log"
        stderr_path = self.output / f"{name}.stderr.log"
        stdout_stream = stdout_path.open("w", encoding="utf-8")
        stderr_stream = stderr_path.open("w", encoding="utf-8")
        try:
            process = subprocess.Popen(
                command,
                cwd=self.repository,
                stdin=subprocess.DEVNULL,
                stdout=stdout_stream,
                stderr=stderr_stream,
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception:
            stdout_stream.close()
            stderr_stream.close()
            raise
        self.summary["commands"].append({"name": name, "command": command})
        return ManagedProcess(process, stdout_path, stderr_path, stdout_stream, stderr_stream)

    def stop_process(self, managed: ManagedProcess, grace_seconds: float = 5.0) -> None:
        if managed.process.poll() is None:
            managed.process.terminate()
            try:
                managed.process.wait(grace_seconds)
            except subprocess.TimeoutExpired:
                managed.process.kill()
                managed.process.wait(5.0)
        managed.close_streams()

    def prepare_game(self) -> tuple[int, int]:
        game_directory = self.args.game_dir.resolve()
        pids = CodolGame.running_pids()
        client_pids = CodolGame.role_pids(game_directory, "client")
        dedicated_pids = CodolGame.role_pids(game_directory, "dedicated")
        if getattr(self.args, "require_active_world", False) and (
            len(client_pids) != 1 or len(dedicated_pids) != 1
        ):
            raise ProtocolFailure(
                "fast regression mode requires one running CODOL client and one dedicated "
                "process; it will not launch or repair the topology"
            )
        must_restart = self.args.clean_launch or self.args.install
        game_tool = self.repository / "tools" / "runtime" / "CodolGame.py"

        if must_restart and pids:
            self.run_command(
                "stop_game_before_prepare",
                [sys.executable, str(game_tool), "stop", "--game-dir", str(game_directory)],
                20.0,
            )
            pids = []
            client_pids = []
            dedicated_pids = []

        if self.args.install:
            install_script = self.repository / "tools" / "distribution" / "InstallCodolRuntime.ps1"
            install_arguments = ["-GameDirectory", str(game_directory), "-Mode", self.args.mode]
            if self.args.skip_build:
                install_arguments.append("-SkipBuild")
            self.run_command(
                "install_runtime",
                powershell_file_command(install_script, *install_arguments),
                self.args.build_timeout,
            )

        if not pids:
            self.backend_log_offset = (
                self.backend_log_path.stat().st_size if self.backend_log_path.is_file() else 0
            )
            self.backend_log_scan_offset = self.backend_log_offset
            self.run_command(
                "launch_dedicated_pair",
                [
                    sys.executable,
                    str(game_tool),
                    "launch-dedicated",
                    "--game-dir",
                    str(game_directory),
                    "--wait",
                    str(self.args.launch_wait),
                    "--launch-mode",
                    self.args.launch_mode,
                ],
                self.args.launch_wait + 45.0,
            )
            self.started_game = True
            pids = CodolGame.running_pids()
            client_pids = CodolGame.role_pids(game_directory, "client")
            dedicated_pids = CodolGame.role_pids(game_directory, "dedicated")

        if len(client_pids) != 1 or len(dedicated_pids) != 1:
            raise CommandFailure(
                "expected one tracked CODOL client and one dedicated process, found "
                f"client={client_pids}, dedicated={dedicated_pids}, all={pids}"
            )
        expected = {client_pids[0], dedicated_pids[0]}
        if set(pids) != expected:
            raise CommandFailure(
                f"unexpected CODOL processes outside the tracked pair: all={pids}, pair={sorted(expected)}"
            )
        return client_pids[0], dedicated_pids[0]

    def frontend_marker(self) -> str | None:
        if not self.started_game:
            return "existing process"
        if self.frontend_marker_line is not None:
            return self.frontend_marker_line
        if self.backend_log_scan_offset is None or not self.backend_log_path.is_file():
            return None
        size = self.backend_log_path.stat().st_size
        offset = self.backend_log_scan_offset if size >= self.backend_log_scan_offset else 0
        with self.backend_log_path.open("rb") as stream:
            stream.seek(offset)
            text = stream.read().decode("utf-8", errors="replace")
        self.backend_log_scan_offset = max(0, size - 256)
        for line in text.splitlines():
            if (
                "LSG_REQUEST" in line
                and "service=71 task=3" in line
                and CLIENT_LOAD_TIME_MARKER in line
            ):
                self.frontend_marker_line = line.strip()[-1000:]
                return self.frontend_marker_line
        return None

    def start_frontend_probe(self, timeout_seconds: float) -> ManagedProcess:
        assert self.client_pid is not None
        match_flow = self.repository / "tools" / "runtime" / "CodolMatchFlow.py"
        command = [
            sys.executable,
            str(match_flow),
            "--pid",
            str(self.client_pid),
            "--action",
            "frontend",
            "--timeout",
            str(timeout_seconds),
            "--frontend-stable-seconds",
            str(self.args.frontend_stable_seconds),
        ]
        if self.args.character_index is not None:
            command.extend(("--character-index", str(self.args.character_index)))
        return self.start_process(
            "frontend_probe",
            command,
        )

    def wait_for_frontend(self) -> dict[str, Any]:
        assert self.client_pid is not None
        timeout_seconds = self.args.frontend_timeout if self.started_game else min(
            self.args.frontend_timeout,
            self.args.reuse_frontend_timeout,
        )
        deadline = time.monotonic() + timeout_seconds
        self.frontend_probe = self.start_frontend_probe(timeout_seconds)
        marker = self.frontend_marker()
        while marker is None:
            events = json_objects(
                self.frontend_probe.stdout_path.read_text(encoding="utf-8", errors="replace")
            )
            latest = events[-1] if events else {}
            state = latest.get("state") if isinstance(latest, dict) else None
            self.emit_progress(
                "waiting_frontend_telemetry",
                probe_event=latest.get("type") if isinstance(latest, dict) else None,
                cinematic_active=(
                    state.get("cinematic_active") if isinstance(state, dict) else None
                ),
                lobby_logon_state=(
                    state.get("lobby", {}).get("logon_state")
                    if isinstance(state, dict) and isinstance(state.get("lobby"), dict)
                    else None
                ),
                remaining_seconds=round(max(0.0, deadline - time.monotonic()), 1),
            )
            if self.client_pid not in CodolGame.running_pids():
                raise CommandFailure("CODOL client exited while waiting for frontend telemetry")
            probe_returncode = self.frontend_probe.process.poll()
            if probe_returncode not in (None, 0):
                raise CommandFailure(
                    f"native frontend probe exited before telemetry with code {probe_returncode}"
                )
            if time.monotonic() >= deadline:
                raise WorkflowTimeout(
                    f"frontend ClientLoadTime telemetry was not observed within "
                    f"{timeout_seconds}s"
                )
            time.sleep(0.1)
            marker = self.frontend_marker()

        probe_deadline = deadline + 5.0
        while self.frontend_probe.process.poll() is None:
            marker = self.frontend_marker() or marker
            events = json_objects(
                self.frontend_probe.stdout_path.read_text(encoding="utf-8", errors="replace")
            )
            latest = events[-1] if events else {}
            state = latest.get("state") if isinstance(latest, dict) else None
            self.emit_progress(
                "waiting_frontend",
                probe_event=latest.get("type") if isinstance(latest, dict) else None,
                connection_state=state.get("connection_state") if isinstance(state, dict) else None,
                cinematic_active=(
                    state.get("cinematic_active") if isinstance(state, dict) else None
                ),
                lobby_logon_state=(
                    state.get("lobby", {}).get("logon_state")
                    if isinstance(state, dict) and isinstance(state.get("lobby"), dict)
                    else None
                ),
                public_profile_ready=(
                    state.get("public_profile_ready") if isinstance(state, dict) else None
                ),
                public_profile_operation=(
                    state.get("public_profile", {}).get("operation")
                    if isinstance(state, dict) and isinstance(state.get("public_profile"), dict)
                    else None
                ),
                public_profile_parsed=(
                    state.get("public_profile", {}).get("parsed")
                    if isinstance(state, dict) and isinstance(state.get("public_profile"), dict)
                    else None
                ),
                public_profile_chunk_mask=(
                    state.get("public_profile", {}).get("chunk_mask")
                    if isinstance(state, dict) and isinstance(state.get("public_profile"), dict)
                    else None
                ),
                quick_match_ready=state.get("quick_match_ready") if isinstance(state, dict) else None,
                remaining_seconds=round(max(0.0, probe_deadline - time.monotonic()), 1),
            )
            if self.client_pid not in CodolGame.running_pids():
                raise CommandFailure("CODOL client exited while waiting for native frontend state")
            if time.monotonic() >= probe_deadline:
                self.stop_process(self.frontend_probe)
                raise WorkflowTimeout(
                    f"native frontend probe exceeded {timeout_seconds + 5.0}s"
                )
            time.sleep(0.1)

        returncode = self.frontend_probe.process.returncode
        self.frontend_probe.close_streams()
        stdout = self.frontend_probe.stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = self.frontend_probe.stderr_path.read_text(encoding="utf-8", errors="replace")
        events = json_objects(stdout)
        ready = next(
            (row for row in reversed(events) if row.get("type") == "frontend_ready"),
            None,
        )
        marker = self.frontend_marker() or marker
        self.summary["frontend_probe"] = {
            "source": "codol-native-quick-match-state",
            "returncode": returncode,
            "events": events[-20:],
            "client_load_time_marker": marker,
            "stderr": stderr[-4000:],
        }
        if returncode != 0:
            if any(row.get("type") == "timeout" for row in events):
                raise WorkflowTimeout(
                    f"native frontend state was not ready within {timeout_seconds}s"
                )
            detail = stderr.strip().splitlines()[-1] if stderr.strip() else "no error detail"
            raise CommandFailure(f"native frontend probe exited with code {returncode}: {detail}")
        state = ready.get("state") if isinstance(ready, dict) else None
        if not quick_match_frontend_ready(state):
            raise CommandFailure("native frontend probe returned without a valid QuickMatch state")
        if self.started_game and marker is None:
            raise CommandFailure("current launch reached native frontend without ClientLoadTime telemetry")
        return state

    def start_tracer(self) -> ManagedProcess:
        assert self.client_pid is not None
        tracer = self.repository / "references" / "client_probe" / "CodolNetchanTrace.py"
        command = [
            sys.executable,
            str(tracer),
            "--pid",
            str(self.client_pid),
            "--duration",
            "0",
            "--log",
            str(self.trace_path),
            "--cbuf-log",
            str(self.cbuf_trace_path),
            "--stop-file",
            str(self.trace_stop_path),
        ]
        return self.start_process(
            "netchan_tracer",
            command,
        )

    def start_asset_tracer(self) -> ManagedProcess:
        assert self.dedicated_pid is not None
        tracer = self.repository / "references" / "client_probe" / "CodolNetchanTrace.py"
        return self.start_process(
            "dedicated_asset_tracer",
            [
                sys.executable,
                str(tracer),
                "--pid",
                str(self.dedicated_pid),
                "--duration",
                "0",
                "--log",
                str(self.asset_trace_path),
                "--stop-file",
                str(self.asset_trace_stop_path),
                "--asset-watch-only",
            ],
        )

    def wait_for_asset_trace_ready(self) -> None:
        assert self.asset_tracer is not None
        deadline = time.monotonic() + self.args.trace_ready_timeout
        while time.monotonic() < deadline:
            events = read_jsonl(self.asset_trace_path)
            if any(row.get("event") == "ready" for row in events):
                self.summary["dedicated_asset_trace_armed_at"] = utc_now()
                return
            returncode = self.asset_tracer.process.poll()
            if returncode is not None:
                self.asset_tracer.close_streams()
                raise CommandFailure(
                    f"dedicated asset tracer exited before armed with code {returncode}"
                )
            time.sleep(0.1)
        raise WorkflowTimeout(
            "dedicated asset tracer did not emit ready within "
            f"{self.args.trace_ready_timeout}s"
        )

    def wait_for_trace_ready(self) -> None:
        assert self.tracer is not None
        deadline = time.monotonic() + self.args.trace_ready_timeout
        while time.monotonic() < deadline:
            self.emit_progress(
                "arming_netchan_tracer",
                remaining_seconds=round(max(0.0, deadline - time.monotonic()), 1),
            )
            events = {row.get("event") for row in read_jsonl(self.trace_path)}
            cbuf_events = {row.get("event") for row in read_jsonl(self.cbuf_trace_path)}
            # Both files are written by one Frida session. The script's ready event
            # can race the Python-side attached append in the busy packet log, while
            # the low-volume Cbuf log reliably preserves both lifecycle markers.
            if "ready" in events and {"ready", "attached"} <= cbuf_events:
                self.summary["trace_armed_at"] = utc_now()
                self.summary["cbuf_trace_armed_at"] = utc_now()
                return
            returncode = self.tracer.process.poll()
            if returncode is not None:
                self.tracer.close_streams()
                raise CommandFailure(f"netchan tracer exited before armed with code {returncode}")
            time.sleep(0.1)
        raise WorkflowTimeout(
            "netchan/Cbuf tracer did not emit ready and attached within "
            f"{self.args.trace_ready_timeout}s"
        )

    def start_server_watcher(self) -> ManagedProcess:
        assert self.dedicated_pid is not None
        control = self.repository / "tools" / "runtime" / "CodolGameServerControl.py"
        command = [
            sys.executable,
            str(control),
            "--pid",
            str(self.dedicated_pid),
            "--watch-log",
            str(self.server_samples_path),
            "--watch-interval",
            str(self.args.sample_interval),
            "--watch-seconds",
            "0",
            "--stop-file",
            str(self.server_watch_stop_path),
        ]
        for entity_num in self.args.watch_damage_entity_num:
            command.extend(["--damage-entity-num", str(entity_num)])
        return self.start_process(
            "server_watcher",
            command,
        )

    def wait_for_server_watch_ready(self) -> None:
        assert self.server_watcher is not None
        deadline = time.monotonic() + self.args.trace_ready_timeout
        while time.monotonic() < deadline:
            self.emit_progress(
                "arming_server_watcher",
                remaining_seconds=round(max(0.0, deadline - time.monotonic()), 1),
            )
            if any(
                row.get("returncode") == 0
                and isinstance(row.get("payload"), dict)
                and row["payload"].get("ok") is True
                and isinstance(row["payload"].get("after"), dict)
                and row["payload"]["after"].get("installed") is True
                for row in read_jsonl(self.server_samples_path)
            ):
                self.summary["server_watch_armed_at"] = utc_now()
                return
            returncode = self.server_watcher.process.poll()
            if returncode is not None:
                self.server_watcher.close_streams()
                raise CommandFailure(f"server watcher exited before armed with code {returncode}")
            time.sleep(0.1)
        raise WorkflowTimeout(
            f"server watcher did not emit a valid sample within {self.args.trace_ready_timeout}s"
        )

    def start_match(self, frontend_state: dict[str, Any]) -> ManagedProcess:
        assert self.client_pid is not None
        match_tool = self.repository / "tools" / "runtime" / "CodolMatchFlow.py"
        self.match_action = (
            "resume"
            if frontend_state.get("active") is True
            and isinstance(frontend_state.get("player_count"), int)
            and frontend_state["player_count"] >= 1
            else "full"
        )
        self.match_trigger_state = frontend_state
        command = [
            sys.executable,
            str(match_tool),
            "--pid",
            str(self.client_pid),
            "--action",
            self.match_action,
            "--playlist-id",
            str(self.args.playlist_id),
            "--timeout",
            str(self.args.match_timeout),
        ]
        if self.args.force_client_allocation:
            command.append("--force-client-allocation")
        if self.args.character_index is not None:
            command.extend(("--character-index", str(self.args.character_index)))
        return self.start_process(
            "match_flow",
            command,
        )

    def monitor_match(self) -> None:
        assert self.match is not None and self.tracer is not None and self.server_watcher is not None
        allocation_started = time.monotonic()
        deadline = time.monotonic() + self.args.match_timeout + 10.0
        while self.match.process.poll() is None:
            events = json_objects(
                self.match.stdout_path.read_text(encoding="utf-8", errors="replace")
            )
            latest = events[-1] if events else {}
            state = latest.get("state") if isinstance(latest, dict) else None
            self.emit_progress(
                "waiting_allocation",
                elapsed_seconds=round(time.monotonic() - allocation_started, 1),
                remaining_seconds=round(max(0.0, deadline - time.monotonic()), 1),
                match_event=latest.get("type") if isinstance(latest, dict) else None,
                room_active=state.get("active") if isinstance(state, dict) else None,
                room_player_count=(
                    state.get("player_count") if isinstance(state, dict) else None
                ),
                room_ready=state.get("ready") if isinstance(state, dict) else None,
            )
            if self.tracer.process.poll() is not None:
                raise self.watcher_exit_failure(
                    "netchan tracer", self.tracer, "client", self.client_pid
                )
            if self.server_watcher.process.poll() is not None:
                raise self.watcher_exit_failure(
                    "server watcher", self.server_watcher, "dedicated", self.dedicated_pid
                )
            now = time.monotonic()
            if now >= deadline:
                self.stop_process(self.match)
                raise WorkflowTimeout(f"match flow exceeded {self.args.match_timeout + 10.0}s")
            time.sleep(0.1)

        returncode = self.match.process.returncode
        self.summary["phase_durations_seconds"]["allocation_wait"] = round(
            time.monotonic() - allocation_started, 3
        )
        self.match.close_streams()
        stdout = self.match.stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = self.match.stderr_path.read_text(encoding="utf-8", errors="replace")
        events = json_objects(stdout)
        self.summary["match"] = {
            "returncode": returncode,
            "events": events,
            "stderr": stderr[-4000:],
        }
        if returncode != 0:
            if any(row.get("type") == "timeout" for row in events):
                raise WorkflowTimeout(
                    f"natural match flow did not observe allocation within {self.args.match_timeout}s"
                )
            raise CommandFailure(f"natural match flow exited with code {returncode}")
        allocation = next(
            (row for row in reversed(events) if row.get("type") == "allocation_observed"),
            None,
        )
        match_invoked = next(
            (row for row in reversed(events) if row.get("type") == "match_invoked"),
            None,
        )
        allocation_source = allocation.get("source") if allocation else None
        if not allocation_source_allowed(
            self.args.force_client_allocation, allocation_source
        ):
            raise CommandFailure("match flow did not observe an allowed allocation source")
        self.summary["allocation_evidence_level"] = allocation_source
        trigger_state = (
            match_invoked.get("frontend_state")
            if match_invoked
            else self.match_trigger_state
        )
        if not isinstance(trigger_state, dict) or trigger_state.get("quick_match_ready") is not True:
            raise CommandFailure("match flow did not preserve its native frontend trigger state")
        self.summary["frontend_probe"]["trigger_state"] = trigger_state
        booking = allocation.get("booking")
        booking = booking if isinstance(booking, dict) else {}
        map_name = booking.get("map_name")
        game_type = booking.get("game_type")
        self.summary["world_identity"] = {
            "map": map_name if isinstance(map_name, str) and map_name else None,
            "gametype": game_type if isinstance(game_type, str) and game_type else None,
            "source": "allocation_booking",
        }
        self.emit_progress(
            "allocation_observed",
            force=True,
            source=allocation.get("source"),
            map_name=map_name,
            game_type=game_type,
        )

        self.monitor_world_boundary("client-native allocation")

    def reuse_active_world(self, frontend_state: dict[str, Any]) -> bool:
        if frontend_state.get("connection_state") != 10:
            return False
        assert self.tracer is not None and self.server_watcher is not None
        deadline = time.monotonic() + self.args.trace_ready_timeout
        while time.monotonic() < deadline:
            if self.tracer.process.poll() is not None:
                raise self.watcher_exit_failure(
                    "netchan tracer", self.tracer, "client", self.client_pid
                )
            if self.server_watcher.process.poll() is not None:
                raise self.watcher_exit_failure(
                    "server watcher", self.server_watcher, "dedicated", self.dedicated_pid
                )
            samples = read_jsonl(self.server_samples_path)
            sample = samples[-1] if samples else {}
            trace_events = read_jsonl(self.trace_path)
            if active_world_reusable(frontend_state, sample, trace_events):
                self.match_action = "reuse_world"
                self.match_trigger_state = frontend_state
                self.summary["evidence_level"] = "existing-active-world"
                self.summary["world_reuse"] = {
                    "evidence_level": "existing-active-world",
                    "reused_at": utc_now(),
                    "server_status": sample.get("payload"),
                }
                self.summary["world_identity"] = {
                    "map": None,
                    "gametype": None,
                    "source": "unavailable_for_reused_world",
                }
                self.emit_progress(
                    "active_world_reused",
                    force=True,
                    evidence_level="existing-active-world",
                )
                self.monitor_world_boundary("existing active world")
                return True
            time.sleep(0.1)
        raise ProtocolFailure(
            "client reports an active world, but server and parser state did not confirm "
            "a reusable world boundary"
        )

    def acquire_world(self, frontend_state: dict[str, Any]) -> None:
        if self.reuse_active_world(frontend_state):
            return
        if getattr(self.args, "require_active_world", False):
            raise ProtocolFailure(
                "no reusable active world is available; fast regression mode will not "
                "start QuickMatch or allocation"
            )
        self.match = self.start_match(frontend_state)
        self.monitor_match()

    def monitor_world_boundary(self, source_description: str) -> None:
        assert self.tracer is not None and self.server_watcher is not None

        capture_started = time.monotonic()
        boundary_deadline = capture_started + self.args.gamestate_timeout
        boundary_reached_at: float | None = None
        stability_deadline: float | None = None
        progress_tracker: ProtocolProgressTracker | None = None
        while True:
            if self.tracer.process.poll() is not None:
                raise self.watcher_exit_failure(
                    "netchan tracer", self.tracer, "client", self.client_pid
                )
            if self.server_watcher.process.poll() is not None:
                raise self.watcher_exit_failure(
                    "server watcher", self.server_watcher, "dedicated", self.dedicated_pid
                )
            samples = read_jsonl(self.server_samples_path)
            sample = samples[-1] if samples else {}
            trace_events = read_jsonl(self.trace_path)
            parser_status = parser_trace_status(trace_events)
            now = time.monotonic()
            if parser_status["overflow_events"]:
                self.summary["parser_boundary"] = parser_status
                raise ProtocolFailure(
                    "client snapshot parser reported a non-zero overflow flag"
                )
            if boundary_reached_at is None and world_boundary_reached(sample, trace_events):
                boundary_reached_at = now
                stability_deadline = now + self.args.post_gamestate_seconds
                progress_tracker = ProtocolProgressTracker(
                    self.args.traffic_stall_seconds, now
                )
                self.summary["parser_boundary"] = parser_status
                self.summary["world_boundary"] = {
                    "reached_at": utc_now(),
                    "server_status": sample.get("payload"),
                }
                self.emit_progress(
                    "world_boundary_reached",
                    force=True,
                    snapshot_messages_sent=(
                        sample.get("payload", {}).get("after", {}).get(
                            "snapshot_messages_sent", 0
                        )
                    ),
                    stability_seconds=self.args.post_gamestate_seconds,
                )
            if progress_tracker is not None:
                stall_reason = progress_tracker.observe(sample, now)
                if stall_reason is not None:
                    self.summary["protocol_stall"] = {
                        "detected_at": utc_now(),
                        "reason": stall_reason,
                        "server_status": sample.get("payload"),
                    }
                    raise ProtocolFailure(stall_reason)
            if stability_deadline is not None and now >= stability_deadline:
                self.summary["stability_window"] = {
                    "requested_seconds": self.args.post_gamestate_seconds,
                    "observed_seconds": round(now - boundary_reached_at, 3),
                    "final_server_status": sample.get("payload"),
                }
                break
            payload = sample.get("payload")
            payload = payload if isinstance(payload, dict) else {}
            after = payload.get("after")
            after = after if isinstance(after, dict) else {}
            ingress = after.get("client_ingress")
            ingress_client = ingress[0] if isinstance(ingress, list) and ingress else {}
            ingress_client = ingress_client if isinstance(ingress_client, dict) else {}
            self.emit_progress(
                "stability_capture" if boundary_reached_at is not None else "waiting_world_boundary",
                elapsed_seconds=round(now - capture_started, 1),
                snapshot_messages_sent=after.get("snapshot_messages_sent", 0),
                accepted_packets=ingress_client.get("accepted_packets", 0),
            )
            if boundary_reached_at is None and now >= boundary_deadline:
                self.summary["phase_durations_seconds"]["post_match_capture"] = round(
                    now - capture_started, 3
                )
                raise WorkflowTimeout(
                    "server did not reach active client, gamestate update, and world spawn boundary "
                    f"within {self.args.gamestate_timeout}s after {source_description}"
                )
            next_deadline = stability_deadline or boundary_deadline
            time.sleep(min(0.2, max(0.0, next_deadline - now)))
        self.summary["phase_durations_seconds"]["post_match_capture"] = round(
            time.monotonic() - capture_started, 3
        )

    def dispatch_forced_reliable_command(self) -> None:
        if self.args.forced_reliable_command is None:
            return
        assert self.client_pid is not None
        requested_command = self.args.forced_reliable_command
        try:
            command = normalize_reliable_command(requested_command)
        except ValueError as error:
            raise ProtocolFailure(str(error)) from error
        baseline_samples = read_jsonl(self.server_samples_path)
        baseline_status = latest_server_status(baseline_samples)
        baseline_client = latest_server_client(baseline_samples)
        if forced_loadout_available(command, baseline_status) is False:
            preparation = baseline_status["loadout_preparation"]
            raise ProtocolFailure(
                f"forced loadout {menu_response_target(command)!r} is not registered for "
                f"prepared character {preparation.get('prepared_character')} "
                f"(class mask 0x{preparation['registered_class_mask']:x})"
            )
        baseline_reliable = (
            baseline_client.get("last_reliable_command")
            if isinstance(baseline_client, dict)
            else None
        )
        baseline_sequence = (
            baseline_reliable.get("sequence")
            if isinstance(baseline_reliable, dict)
            else None
        )
        baseline_menu_response = (
            baseline_client.get("last_menu_response")
            if isinstance(baseline_client, dict)
            else None
        )
        baseline_menu_sequence = (
            baseline_menu_response.get("sequence")
            if isinstance(baseline_menu_response, dict)
            else None
        )
        if forced_command_target_satisfied(command, baseline_client):
            self.summary["forced_reliable_command"] = {
                "status": "already_satisfied",
                "dispatch_skipped": True,
                "requested_command": requested_command,
                "command": command,
                "observation_source": "server-watcher-before-trigger",
                "baseline_reliable_sequence": baseline_sequence,
                "baseline_menu_response_sequence": baseline_menu_sequence,
                "observed": baseline_reliable,
                "menu_response": baseline_client.get("last_menu_response"),
                "gameplay": baseline_client.get("gameplay"),
            }
            self.emit_progress(
                "forced_reliable_command_already_satisfied",
                force=True,
                command=command,
            )
            return

        tool = self.repository / "tools" / "runtime" / "CodolClientCommand.py"
        result = self.run_command(
            "forced_reliable_command",
            [
                sys.executable,
                str(tool),
                "--pid",
                str(self.client_pid),
                "--timeout",
                str(self.args.forced_command_timeout),
                f"cmd {command}",
            ],
            self.args.forced_command_timeout + 5.0,
        )
        rows = json_objects(result.stdout)
        invocation = rows[-1] if rows else None
        if not isinstance(invocation, dict) or invocation.get("ok") is not True:
            raise CommandFailure("forced reliable command did not report a successful native dispatch")

        deadline = time.monotonic() + self.args.forced_command_timeout
        while time.monotonic() < deadline:
            if self.client_pid not in CodolGame.running_pids():
                raise CommandFailure("CODOL client exited after forced reliable command dispatch")
            samples = read_jsonl(self.server_samples_path)
            for sample in reversed(samples):
                payload = sample.get("payload")
                after = payload.get("after") if isinstance(payload, dict) else None
                ingress = after.get("client_ingress") if isinstance(after, dict) else None
                client = ingress[0] if isinstance(ingress, list) and ingress else None
                reliable = client.get("last_reliable_command") if isinstance(client, dict) else None
                gameplay = client.get("gameplay") if isinstance(client, dict) else None
                menu_response = (
                    client.get("last_menu_response") if isinstance(client, dict) else None
                )
                menu_target = menu_response_target(command)
                if menu_target is None:
                    observed = (
                        isinstance(reliable, dict)
                        and reliable.get("command") == command
                        and reliable_sequence_advanced(
                            reliable.get("sequence"), baseline_sequence
                        )
                    )
                else:
                    observed = (
                        isinstance(menu_response, dict)
                        and reliable_sequence_advanced(
                            menu_response.get("sequence"), baseline_menu_sequence
                        )
                        and forced_command_target_satisfied(command, client)
                    )
                if observed:
                    self.summary["forced_reliable_command"] = {
                        "status": "dispatched_and_observed",
                        "dispatch_skipped": False,
                        "evidence_level": "client-native-forced",
                        "requested_command": requested_command,
                        "command": command,
                        "baseline_reliable_sequence": baseline_sequence,
                        "baseline_menu_response_sequence": baseline_menu_sequence,
                        "invocation": invocation,
                        "observed": (
                            reliable
                            if isinstance(reliable, dict)
                            and reliable.get("command") == command
                            else None
                        ),
                        "menu_response": menu_response,
                        "gameplay": gameplay,
                    }
                    self.emit_progress(
                        "forced_reliable_command_observed",
                        force=True,
                        command=command,
                    )
                    return
            time.sleep(0.1)
        raise WorkflowTimeout(
            "server did not observe the forced reliable command within "
            f"{self.args.forced_command_timeout:g}s"
        )

    def exercise_client_input(self) -> None:
        input_action = getattr(self.args, "input_action", None)
        input_scenario_path = getattr(self.args, "input_scenario", None)
        if input_action is None and input_scenario_path is None:
            return
        if input_action is not None and input_scenario_path is not None:
            raise CommandFailure("input action and input scenario are mutually exclusive")

        scenario: dict[str, Any]
        scenario_snapshot_path: Path | None = None
        scenario_sha256: str | None = None
        if input_scenario_path is not None:
            frozen = self.freeze_input_scenario()
            if frozen is None:
                raise CommandFailure("input scenario snapshot is unavailable")
            scenario, scenario_snapshot_path = frozen
            scenario_sha256 = str(self.summary["input_scenario"]["sha256"])
            input_duration = scenario_duration_seconds(scenario)
            progress_details = {
                "scenario": scenario["name"],
                "scenario_path": str(scenario_snapshot_path),
                "scenario_sha256": scenario_sha256,
            }
        else:
            assert input_action is not None
            scenario = single_action_scenario(
                input_action,
                self.args.input_hold_seconds,
                self.args.input_observe_seconds,
            )
            input_duration = scenario_duration_seconds(scenario)
            progress_details = {"action": input_action}

        assert self.client_pid is not None
        self.emit_progress(
            "preparing_input_exercise",
            force=True,
            **progress_details,
        )
        if getattr(self.args, "frame_trace", False):
            self.start_input_frame_trace(
                input_duration + FRAME_TRACE_RUNTIME_GRACE_SECONDS
            )
        tool = self.repository / "tools" / "runtime" / "CodolClientInput.py"
        output = self.output / "client_input.json"
        input_timeout = input_duration + 8.0
        process_timeout = input_timeout + 4.0
        command = [sys.executable, str(tool)]
        if input_scenario_path is not None:
            assert scenario_snapshot_path is not None
            assert scenario_sha256 is not None
            command.extend(
                [
                    "--scenario",
                    str(scenario_snapshot_path),
                    "--scenario-sha256",
                    scenario_sha256,
                ]
            )
        else:
            command.extend(
                [
                    input_action,
                    "--hold-seconds",
                    str(self.args.input_hold_seconds),
                    "--observe-seconds",
                    str(self.args.input_observe_seconds),
                ]
            )
        command.extend(
            [
                "--pid",
                str(self.client_pid),
                "--sample-interval",
                str(self.args.input_sample_interval),
                "--timeout",
                str(input_timeout),
                "--output",
                str(output),
            ]
        )
        timed_out = False
        try:
            result = self.run_command(
                "client_input", command, process_timeout, required=False
            )
        except subprocess.TimeoutExpired:
            timed_out = True
            result = None
        try:
            if output.is_file():
                payload = json.loads(output.read_text(encoding="utf-8"))
            elif result is not None:
                payload = json.loads(result.stdout)
            else:
                raise json.JSONDecodeError("missing checkpoint", "", 0)
        except (OSError, json.JSONDecodeError) as error:
            raise CommandFailure("client input exercise returned invalid JSON") from error
        if getattr(self.args, "frame_trace", False):
            self.finish_input_frame_trace()
        if timed_out:
            payload["subprocess_timed_out"] = True
        self.summary["client_input"] = {
            **payload,
            "evidence_level": "client-native-forced",
            "parent_validation": {
                "raw_capture_integrity": False,
                "gameplay_conformance_evaluated": False,
            },
        }
        self.write_summary_checkpoint()
        parser = payload.get("parser_summary")
        if timed_out:
            raise ProtocolFailure(
                "client input probe timed out; the last checkpoint was preserved"
            )
        if payload.get("ok") is not True or payload.get("final_event") != "completed":
            raise CommandFailure("client input exercise did not complete and release input")
        if payload.get("process_exited") or payload.get(
            "process_alive_after_observation"
        ) is not True:
            raise ProtocolFailure("client input exercise caused the client process to exit")
        events = payload.get("events")
        if not isinstance(events, list) or not any(
            isinstance(event, dict)
            and event.get("event") == "armed"
            and event.get("ok") is True
            for event in events
        ):
            raise ProtocolFailure("client input exercise did not reach the armed state")
        terminal_events = [
            event
            for event in events
            if isinstance(event, dict)
            and event.get("event") in {"completed", "aborted", "error"}
        ]
        if (
            len(terminal_events) != 1
            or terminal_events[0].get("event") != payload.get("final_event")
            or terminal_events[0].get("ok") is not True
        ):
            raise ProtocolFailure(
                "client input terminal event history does not match final_event"
            )
        dispatched_events = [
            event
            for event in events
            if isinstance(event, dict)
            and event.get("event")
            in {"input-activate", "input-down", "input-release", "input-up"}
        ]
        if [event.get("scenario_event_index") for event in dispatched_events] != list(
            range(len(scenario["events"]))
        ) or any(
            event.get("action") != expected["action"]
            or event.get("transition") != expected["transition"]
            for event, expected in zip(dispatched_events, scenario["events"])
        ):
            raise ProtocolFailure("client input scenario dispatch lifecycle is incomplete")
        if not isinstance(parser, dict):
            raise ProtocolFailure("client input exercise did not report parser boundaries")
        if parser.get("overflow_events") != 0:
            raise ProtocolFailure("client input exercise observed a parser overflow")
        if parser.get("com_error_count") != 0:
            raise ProtocolFailure("client input exercise reached Com_Error")
        if not input_parser_boundary_complete(parser):
            raise ProtocolFailure(
                "client input exercise did not observe a complete accepted outer parser boundary"
            )
        if input_scenario_path is not None:
            if payload.get("scenario_source_sha256") != scenario_sha256:
                raise ProtocolFailure(
                    "input scenario child did not verify the frozen snapshot SHA-256"
                )

        timing = payload.get("scenario_timing")
        expected_group_count = len({int(event["at_ms"]) for event in scenario["events"]})
        if (
            not isinstance(timing, dict)
            or timing.get("valid") is not True
            or timing.get("overdue_event_group_count") != 0
            or timing.get("dispatched_event_group_count") != expected_group_count
        ):
            raise ProtocolFailure(
                "input scenario timing was distorted by a stalled client frame"
            )

        capture = payload.get("capture_summary")
        if not isinstance(capture, dict):
            raise ProtocolFailure("client input exercise did not report capture integrity")
        sample_count = capture.get("sample_count")
        opaque_count = capture.get("opaque_evidence_count")
        opaque_bytes = capture.get("opaque_evidence_bytes")
        if (
            not isinstance(sample_count, int)
            or isinstance(sample_count, bool)
            or sample_count <= 0
            or capture.get("sequence_contiguous") is not True
            or not isinstance(opaque_count, int)
            or isinstance(opaque_count, bool)
            or opaque_count != sample_count
            or not isinstance(opaque_bytes, int)
            or isinstance(opaque_bytes, bool)
            or opaque_bytes <= 0
            or capture.get("segment_framing_valid") is not True
        ):
            raise ProtocolFailure("client input opaque evidence is incomplete")
        captured_parser = capture.get("latest_parser_summary")
        if (
            not isinstance(captured_parser, dict)
            or captured_parser.get("overflow_events") != 0
            or captured_parser.get("com_error_count") != 0
            or not input_parser_boundary_complete(captured_parser)
        ):
            raise ProtocolFailure("client input raw capture has an incomplete parser boundary")

        raw_samples = payload.get("raw_samples")
        expected_raw_path = output.with_suffix(".samples.jsonl").resolve()
        expected_blob_path = expected_raw_path.with_suffix(".bin")
        if not isinstance(raw_samples, dict):
            raise ProtocolFailure("client input raw journal status is missing")
        try:
            raw_path = Path(str(raw_samples.get("path"))).resolve()
            blob_path = Path(str(raw_samples.get("blob_path"))).resolve()
        except (OSError, ValueError) as error:
            raise ProtocolFailure("client input raw journal path is invalid") from error
        if (
            raw_path != expected_raw_path
            or blob_path != expected_blob_path
            or raw_samples.get("persisted_sample_count") != sample_count
            or raw_samples.get("persisted_blob_size") != opaque_bytes
            or not raw_path.is_file()
            or not blob_path.is_file()
            or blob_path.stat().st_size != opaque_bytes
        ):
            raise ProtocolFailure("client input raw journal is incomplete")
        try:
            raw_validation = summarize_raw_sample_checkpoint(raw_path)
        except (OSError, ValueError) as error:
            raise ProtocolFailure(
                "client input raw journal failed independent validation"
            ) from error
        recomputed_raw = raw_validation.get("raw_samples")
        if (
            raw_validation.get("integrity_complete") is not True
            or raw_validation.get("scenario") != normalize_scenario(scenario)
            or raw_validation.get("capture_summary") != capture
            or not isinstance(recomputed_raw, dict)
            or recomputed_raw.get("path") != str(expected_raw_path)
            or recomputed_raw.get("blob_path") != str(expected_blob_path)
            or recomputed_raw.get("recovered_sample_count") != sample_count
            or recomputed_raw.get("opaque_evidence_count") != opaque_count
            or recomputed_raw.get("opaque_evidence_bytes") != opaque_bytes
        ):
            raise ProtocolFailure(
                "client input raw journal does not match the captured scenario or summary"
            )
        if (
            scenario_snapshot_path is not None
            and hashlib.sha256(scenario_snapshot_path.read_bytes()).hexdigest()
            != scenario_sha256
        ):
            raise ProtocolFailure("frozen input scenario changed during capture")

        client_input_summary = self.summary["client_input"]
        assert isinstance(client_input_summary, dict)
        client_input_summary["parent_validation"] = {
            "raw_capture_integrity": True,
            "gameplay_conformance_evaluated": False,
        }
        self.write_summary_checkpoint()
        self.emit_progress(
            "input_exercise_completed",
            force=True,
            **progress_details,
            overflow_events=parser.get("overflow_events"),
            validation_scope="raw_capture_integrity_only",
        )

    def start_input_frame_trace(self, duration_seconds: float) -> None:
        assert self.client_pid is not None
        self.emit_progress("arming_frame_trace", force=True)
        tool = self.repository / "references" / "client_probe" / "CodolFrameTrace.py"
        self.frame_trace = self.start_process(
            "frame_trace",
            [
                sys.executable,
                str(tool),
                "--pid",
                str(self.client_pid),
                "--duration",
                str(duration_seconds),
                "--log",
                str(self.frame_trace_path),
            ],
        )
        deadline = time.monotonic() + self.args.trace_ready_timeout
        while time.monotonic() < deadline:
            events = {row.get("event") for row in read_jsonl(self.frame_trace_path)}
            if {"ready", "attached"}.issubset(events):
                self.emit_progress("frame_trace_armed", force=True)
                return
            if self.frame_trace.process.poll() is not None:
                self.frame_trace.close_streams()
                raise CommandFailure(
                    "frame trace exited before reporting ready and attached"
                )
            time.sleep(0.05)
        raise WorkflowTimeout(
            f"frame trace did not arm within {self.args.trace_ready_timeout}s"
        )

    def finish_input_frame_trace(self) -> None:
        if self.frame_trace is None:
            return
        try:
            self.frame_trace.process.wait(5.0)
        except subprocess.TimeoutExpired as error:
            self.stop_process(self.frame_trace)
            raise ProtocolFailure("frame trace did not finish after input") from error
        self.frame_trace.close_streams()
        if self.frame_trace.process.returncode != 0:
            raise CommandFailure(
                f"frame trace exited with code {self.frame_trace.process.returncode}"
            )
        try:
            frame_summary = json.loads(
                self.frame_trace_summary_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise ProtocolFailure("frame trace summary is missing or invalid") from error
        if (
            not isinstance(frame_summary, dict)
            or frame_summary.get("sample_count", 0) < 30
            or frame_summary.get("prediction_sample_count", 0) < 30
        ):
            raise ProtocolFailure("frame trace did not capture the active input window")
        self.summary["frame_trace"] = {
            "path": str(self.frame_trace_path),
            "summary_path": str(self.frame_trace_summary_path),
            "summary": frame_summary,
        }
        self.write_summary_checkpoint()

    def arm_viewmodel_trace(self) -> None:
        if not self.args.viewmodel_trace:
            return
        assert self.client_pid is not None
        self.emit_progress("arming_viewmodel_trace", force=True)
        self.stop_tracer()
        tool = self.repository / "tools" / "runtime" / "CodolViewmodelTrace.py"
        self.viewmodel_probe = self.start_process(
            "viewmodel_trace",
            [
                sys.executable,
                str(tool),
                "--pid",
                str(self.client_pid),
                "--duration",
                "0",
                "--output",
                str(self.viewmodel_trace_path),
                "--ready-file",
                str(self.viewmodel_ready_path),
                "--stop-file",
                str(self.viewmodel_stop_path),
            ],
        )
        deadline = time.monotonic() + self.args.trace_ready_timeout
        while time.monotonic() < deadline:
            self.emit_progress(
                "arming_viewmodel_trace",
                remaining_seconds=round(max(0.0, deadline - time.monotonic()), 1),
            )
            if self.viewmodel_ready_path.is_file():
                self.summary["viewmodel_trace_armed_at"] = utc_now()
                return
            returncode = self.viewmodel_probe.process.poll()
            if returncode is not None:
                self.viewmodel_probe.close_streams()
                raise CommandFailure(
                    f"viewmodel trace exited before armed with code {returncode}"
                )
            time.sleep(0.1)
        raise WorkflowTimeout(
            f"viewmodel trace did not arm within {self.args.trace_ready_timeout}s"
        )

    def finish_viewmodel_trace(self) -> None:
        if not self.args.viewmodel_trace:
            return
        assert self.viewmodel_probe is not None
        deadline = time.monotonic() + self.args.viewmodel_trace_seconds
        while time.monotonic() < deadline:
            self.emit_progress(
                "capturing_viewmodel_trace",
                remaining_seconds=round(max(0.0, deadline - time.monotonic()), 1),
            )
            returncode = self.viewmodel_probe.process.poll()
            if returncode is not None:
                self.viewmodel_probe.close_streams()
                raise CommandFailure(
                    f"viewmodel trace exited during capture with code {returncode}"
                )
            time.sleep(0.1)
        self.viewmodel_stop_path.touch()
        try:
            self.viewmodel_probe.process.wait(10.0)
        except subprocess.TimeoutExpired as error:
            self.stop_process(self.viewmodel_probe)
            raise CommandFailure("viewmodel trace did not stop cleanly") from error
        self.viewmodel_probe.close_streams()
        if self.viewmodel_probe.process.returncode != 0:
            raise CommandFailure(
                f"viewmodel trace exited with code {self.viewmodel_probe.process.returncode}"
            )
        try:
            payload = json.loads(self.viewmodel_trace_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CommandFailure("viewmodel trace returned invalid JSON") from error
        if payload.get("ok") is not True:
            raise CommandFailure("viewmodel trace did not complete")
        counts = payload.get("counts")
        if not isinstance(counts, dict) or counts.get("add_view_weapon", 0) <= 0:
            raise ProtocolFailure("viewmodel trace did not observe CG_AddViewWeapon")
        self.summary["viewmodel_trace"] = payload
        diagnosis = payload.get("diagnosis")
        self.emit_progress(
            "viewmodel_trace_completed",
            force=True,
            diagnosis=(diagnosis.get("result") if isinstance(diagnosis, dict) else None),
        )

    def capture_window(self) -> None:
        assert self.client_pid is not None
        screenshot = self.output / "window.png"
        tool = self.repository / "tools" / "runtime" / "CaptureCodolWindow.py"
        result = self.run_command(
            "capture_window",
            [
                sys.executable,
                str(tool),
                "--pid",
                str(self.client_pid),
                "--output",
                str(screenshot),
            ],
            20.0,
            required=False,
        )
        if result.returncode != 0:
            self.summary["warnings"].append("window capture failed")
        self.summary["screenshot"] = str(screenshot) if screenshot.is_file() else None

    def capture_cgame_state(self) -> None:
        assert self.client_pid is not None
        if self.client_pid not in CodolGame.running_pids():
            self.summary["warnings"].append("cgame state capture skipped because the client exited")
            return
        tool = self.repository / "references" / "client_probe" / "CodolCgameState.py"
        result = self.run_command(
            "capture_cgame_state",
            [sys.executable, str(tool), "--pid", str(self.client_pid)],
            20.0,
            required=False,
        )
        if result.returncode != 0:
            self.summary["warnings"].append("cgame state capture failed")
            return
        try:
            state = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.summary["warnings"].append("cgame state capture returned invalid JSON")
            return
        output = self.output / "cgame_state.json"
        output.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        snap = state.get("snap") if isinstance(state, dict) else None
        self.summary["cgame_state"] = {
            "path": str(output),
            "predicted_player_state": state.get("predicted_player_state"),
            "refdef": state.get("refdef"),
            "snapshot_player_state": snap.get("player_state")
            if isinstance(snap, dict)
            else None,
        }
        snapshot_player_state = self.summary["cgame_state"]["snapshot_player_state"]
        if isinstance(snapshot_player_state, dict):
            snapshot_player_state.pop("prefix_hex", None)

    def stop_tracer(self) -> None:
        if self.tracer is None:
            return
        if self.tracer.process.poll() is None:
            self.trace_stop_path.touch()
            try:
                self.tracer.process.wait(10.0)
            except subprocess.TimeoutExpired:
                self.stop_process(self.tracer)
        self.tracer.close_streams()

    def stop_asset_tracer(self) -> None:
        if self.asset_tracer is None:
            return
        if self.asset_tracer.process.poll() is None:
            self.asset_trace_stop_path.touch()
            try:
                self.asset_tracer.process.wait(10.0)
            except subprocess.TimeoutExpired:
                self.stop_process(self.asset_tracer)
        self.asset_tracer.close_streams()

    def watcher_exit_failure(
        self,
        name: str,
        managed: ManagedProcess,
        role: str,
        expected_pid: int | None,
    ) -> CommandFailure:
        if expected_pid is not None and expected_pid not in CodolGame.running_pids():
            return CommandFailure(f"CODOL {role} exited while {name} was active")
        return CommandFailure(f"{name} exited unexpectedly with code {managed.process.returncode}")

    def stop_server_watcher(self) -> None:
        if self.server_watcher is None:
            return
        if self.server_watcher.process.poll() is None:
            self.server_watch_stop_path.touch()
            try:
                self.server_watcher.process.wait(10.0)
            except subprocess.TimeoutExpired:
                self.stop_process(self.server_watcher)
        self.server_watcher.close_streams()

    def stop_viewmodel_probe(self) -> None:
        if self.viewmodel_probe is None:
            return
        if self.viewmodel_probe.process.poll() is None:
            self.viewmodel_stop_path.touch()
            try:
                self.viewmodel_probe.process.wait(10.0)
            except subprocess.TimeoutExpired:
                self.stop_process(self.viewmodel_probe)
        self.viewmodel_probe.close_streams()

    def stop_frame_trace(self) -> None:
        if self.frame_trace is None:
            return
        if self.frame_trace.process.poll() is None:
            self.stop_process(self.frame_trace)
        else:
            self.frame_trace.close_streams()

    def stop_game_if_owned(self) -> None:
        if not self.started_game or self.args.keep_game_running:
            return
        game_tool = self.repository / "tools" / "runtime" / "CodolGame.py"
        try:
            self.run_command(
                "stop_game_after_capture",
                [
                    sys.executable,
                    str(game_tool),
                    "stop",
                    "--game-dir",
                    str(self.args.game_dir.resolve()),
                ],
                20.0,
            )
        except (OSError, subprocess.TimeoutExpired, CommandFailure) as error:
            self.summary["warnings"].append(f"game cleanup failed: {error}")

    def finalize_summary(self) -> None:
        trace = read_jsonl(self.trace_path)
        asset_trace = read_jsonl(self.asset_trace_path)
        cbuf_trace = read_jsonl(self.cbuf_trace_path)
        cbuf_commands = [row for row in cbuf_trace if row.get("event") == "cbuf_command"]
        cbuf_source_counts: dict[str, int] = {}
        for command in cbuf_commands:
            caller = command.get("caller")
            source = caller.get("kind") if isinstance(caller, dict) else "unknown"
            cbuf_source_counts[str(source)] = cbuf_source_counts.get(str(source), 0) + 1
        samples = read_jsonl(self.server_samples_path)
        successful_samples = [
            row
            for row in samples
            if row.get("returncode") == 0
            and isinstance(row.get("payload"), dict)
            and row["payload"].get("ok") is True
        ]
        self.summary.update(
            {
                "completed_at": utc_now(),
                "output_directory": str(self.output),
                "pid": self.client_pid,
                "client_pid": self.client_pid,
                "dedicated_pid": self.dedicated_pid,
                "game_started_by_orchestrator": self.started_game,
                "trace_event_count": len(trace),
                "trace_events": sorted({row.get("event") for row in trace if row.get("event")}),
                "dedicated_asset_observations": [
                    row
                    for row in asset_trace
                    if row.get("event") == "weapon_group_root_value"
                ],
                "dedicated_asset_trace": {
                    "path": str(self.asset_trace_path),
                    "event_count": len(asset_trace),
                    "events": sorted(
                        {row.get("event") for row in asset_trace if row.get("event")}
                    ),
                    "ready": next(
                        (row for row in asset_trace if row.get("event") == "ready"),
                        None,
                    ),
                },
                "cbuf_trace": {
                    "path": str(self.cbuf_trace_path),
                    "event_count": len(cbuf_trace),
                    "command_count": len(cbuf_commands),
                    "caller_kind_counts": cbuf_source_counts,
                    "last_commands": cbuf_commands[-20:],
                },
                "server_sample_count": len(samples),
                "successful_server_sample_count": len(successful_samples),
                "final_server_status": successful_samples[-1]["payload"] if successful_samples else None,
            }
        )
        self.write_summary_checkpoint()

    def run(self) -> int:
        self.output.mkdir(parents=True, exist_ok=False)
        workflow_started = time.monotonic()
        returncode = 2
        try:
            self.freeze_input_scenario()
            self.emit_progress("preparing_game", force=True, output_directory=str(self.output))
            phase_started = time.monotonic()
            self.client_pid, self.dedicated_pid = self.prepare_game()
            self.summary.update(
                pid=self.client_pid,
                client_pid=self.client_pid,
                dedicated_pid=self.dedicated_pid,
            )
            self.summary["phase_durations_seconds"]["prepare_game"] = round(
                time.monotonic() - phase_started, 3
            )
            self.emit_progress(
                "game_ready",
                force=True,
                client_pid=self.client_pid,
                dedicated_pid=self.dedicated_pid,
            )
            if getattr(self.args, "observe_dedicated_assets", False):
                self.asset_tracer = self.start_asset_tracer()
                self.wait_for_asset_trace_ready()
            phase_started = time.monotonic()
            frontend_state = self.wait_for_frontend()
            self.summary["phase_durations_seconds"]["wait_frontend"] = round(
                time.monotonic() - phase_started, 3
            )
            self.emit_progress("frontend_ready", force=True, client_pid=self.client_pid)
            phase_started = time.monotonic()
            self.tracer = self.start_tracer()
            self.wait_for_trace_ready()
            self.server_watcher = self.start_server_watcher()
            self.wait_for_server_watch_ready()
            self.summary["phase_durations_seconds"]["arm_tracer"] = round(
                time.monotonic() - phase_started, 3
            )
            self.emit_progress(
                "watchers_armed",
                force=True,
                client_pid=self.client_pid,
                dedicated_pid=self.dedicated_pid,
            )
            self.acquire_world(frontend_state)
            self.arm_viewmodel_trace()
            self.dispatch_forced_reliable_command()
            self.finish_viewmodel_trace()
            self.exercise_client_input()
            self.capture_window()
            self.summary["outcome"] = "success"
            returncode = 0
        except WorkflowTimeout as error:
            self.summary.update(outcome="timeout", error=str(error))
        except ProtocolFailure as error:
            self.summary.update(outcome="protocol_failure", error=str(error))
        except (CommandFailure, OSError, subprocess.SubprocessError) as error:
            self.summary.update(outcome="subprocess_failure", error=str(error))
        except Exception as error:
            self.summary.update(outcome="internal_failure", error=repr(error))
        finally:
            self.emit_progress(
                "cleanup",
                force=True,
                outcome=self.summary.get("outcome"),
            )
            if self.match is not None and self.match.process.poll() is None:
                self.stop_process(self.match)
            if self.frontend_probe is not None and self.frontend_probe.process.poll() is None:
                self.stop_process(self.frontend_probe)
            self.summary["trace_before_stop_event_count"] = len(read_jsonl(self.trace_path))
            self.summary["cbuf_trace_before_stop_event_count"] = len(
                read_jsonl(self.cbuf_trace_path)
            )
            if self.client_pid is not None and "screenshot" not in self.summary:
                try:
                    self.capture_window()
                except (OSError, subprocess.SubprocessError) as error:
                    self.summary["warnings"].append(f"window capture failed: {error}")
            if (
                self.args.keep_server_watcher_running
                and self.server_watcher is not None
                and self.server_watcher.process.poll() is None
            ):
                self.summary["retained_server_watcher"] = {
                    "pid": self.server_watcher.process.pid,
                    "log": str(self.server_samples_path),
                    "stop_file": str(self.server_watch_stop_path),
                }
                self.server_watcher.close_streams()
            else:
                self.stop_server_watcher()
            self.stop_tracer()
            self.stop_asset_tracer()
            self.stop_viewmodel_probe()
            self.stop_frame_trace()
            trace_status = parser_trace_status(read_jsonl(self.trace_path))
            if self.client_pid is not None and trace_status["parse_snapshot_enter"] > 0:
                try:
                    self.capture_cgame_state()
                except (OSError, subprocess.SubprocessError) as error:
                    self.summary["warnings"].append(f"cgame state capture failed: {error}")
            self.stop_game_if_owned()
            self.summary["phase_durations_seconds"]["workflow_total"] = round(
                time.monotonic() - workflow_started, 3
            )
            self.summary["current_phase"] = "completed"
            self.finalize_summary()
            self.emit_progress(
                "completed",
                force=True,
                outcome=self.summary.get("outcome"),
                summary=str(self.summary_path),
            )
        return returncode


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=CodolGame.find_game_directory(repository.parent))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--playlist-id", type=int, default=26)
    parser.add_argument("--character-index", type=int)
    parser.add_argument("--install", action="store_true", help="Build and install before launching")
    parser.add_argument("--skip-build", action="store_true", help="With --install, reuse staged build")
    parser.add_argument("--mode", choices=("debug", "release"), default="release")
    parser.add_argument("--clean-launch", action="store_true")
    parser.add_argument("--keep-game-running", action="store_true")
    parser.add_argument(
        "--keep-server-watcher-running",
        action="store_true",
        help="Keep the dedicated status watcher alive and publish its stop-file in summary",
    )
    parser.add_argument(
        "--watch-damage-entity-num",
        type=lambda value: int(value, 0),
        action="append",
        default=[],
        help="Record one entity damage owner in the retained server watcher (repeatable)",
    )
    parser.add_argument(
        "--require-active-world",
        action="store_true",
        help=(
            "Only reuse an already active, parser-confirmed world; fail without starting "
            "QuickMatch, ready, or allocation"
        ),
    )
    parser.add_argument("--launch-mode", choices=("auto", "no-args", "offline"), default="auto")
    parser.add_argument("--launch-wait", type=float, default=20.0)
    parser.add_argument("--frontend-timeout", type=float, default=90.0)
    parser.add_argument("--reuse-frontend-timeout", type=float, default=15.0)
    parser.add_argument("--frontend-stable-seconds", type=float, default=2.0)
    parser.add_argument("--trace-ready-timeout", type=float, default=20.0)
    parser.add_argument(
        "--observe-dedicated-assets",
        action="store_true",
        help=(
            "Run a bounded read-only poll of dedicated weapon-group, registry, and common "
            "zone state through a separately managed tracer"
        ),
    )
    parser.add_argument("--match-timeout", type=float, default=120.0)
    parser.add_argument(
        "--force-client-allocation",
        action="store_true",
        help=(
            "After native QuickMatch and SetReady, call the client's allocation entry "
            "instead of waiting for natural allocation"
        ),
    )
    parser.add_argument("--gamestate-timeout", type=float, default=90.0)
    parser.add_argument("--post-gamestate-seconds", type=float, default=5.0)
    parser.add_argument(
        "--forced-reliable-command",
        help=(
            "After the natural world boundary, queue one server reliable-command payload "
            "through the client's native Cbuf_AddText entry and wait for observation; "
            "a leading 'cmd ' is accepted and removed"
        ),
    )
    parser.add_argument("--forced-command-timeout", type=float, default=5.0)
    parser.add_argument(
        "--viewmodel-trace",
        action="store_true",
        help=(
            "After the world and optional loadout boundary, stop lifecycle watchers and "
            "run one bounded first-person viewmodel construction and scene trace"
        ),
    )
    parser.add_argument("--viewmodel-trace-seconds", type=float, default=2.0)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input-action",
        choices=tuple(ACTION_NAMES),
        help=(
            "After the world and optional loadout boundary, stop lifecycle watchers and "
            "exercise one native binding action with opaque runtime evidence"
        ),
    )
    input_group.add_argument(
        "--input-scenario",
        type=Path,
        help=(
            "After the world boundary, run one versioned native-input scenario with "
            "opaque runtime evidence"
        ),
    )
    parser.add_argument("--input-hold-seconds", type=float, default=0.15)
    parser.add_argument("--input-observe-seconds", type=float, default=2.0)
    parser.add_argument("--input-sample-interval", type=float, default=0.05)
    parser.add_argument(
        "--frame-trace",
        action="store_true",
        help=(
            "Arm CodolFrameTrace before the input exercise and include its prediction "
            "summary in the same run"
        ),
    )
    parser.add_argument("--traffic-stall-seconds", type=float, default=10.0)
    parser.add_argument("--progress-interval", type=float, default=5.0)
    parser.add_argument("--sample-interval", type=float, default=2.0)
    parser.add_argument("--build-timeout", type=float, default=600.0)
    args = parser.parse_args()
    if args.game_dir is None:
        parser.error("could not locate the CODOL game directory; pass --game-dir")
    if args.skip_build and not args.install:
        parser.error("--skip-build requires --install")
    if args.keep_server_watcher_running and not args.keep_game_running:
        parser.error("--keep-server-watcher-running requires --keep-game-running")
    if any(not 0 <= value < 2048 for value in args.watch_damage_entity_num):
        parser.error("every --watch-damage-entity-num must be in [0, 2048)")
    if args.require_active_world and (args.clean_launch or args.install):
        parser.error("--require-active-world cannot be combined with --clean-launch or --install")
    if args.require_active_world and args.force_client_allocation:
        parser.error("--require-active-world cannot be combined with --force-client-allocation")
    if not 0 <= args.playlist_id <= 255:
        parser.error("--playlist-id must fit in one byte")
    if args.character_index is not None and not 0 <= args.character_index < 12:
        parser.error("--character-index must be between 0 and 11")
    for name in (
        "launch_wait",
        "frontend_timeout",
        "reuse_frontend_timeout",
        "trace_ready_timeout",
        "match_timeout",
        "gamestate_timeout",
        "sample_interval",
        "progress_interval",
        "build_timeout",
        "forced_command_timeout",
        "input_sample_interval",
        "viewmodel_trace_seconds",
    ):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.frontend_stable_seconds < 0:
        parser.error("--frontend-stable-seconds must be non-negative")
    if args.post_gamestate_seconds < 0:
        parser.error("--post-gamestate-seconds must be non-negative")
    if args.input_hold_seconds < 0:
        parser.error("--input-hold-seconds must be non-negative")
    if args.input_observe_seconds < 0:
        parser.error("--input-observe-seconds must be non-negative")
    if args.frame_trace and args.input_action is None and args.input_scenario is None:
        parser.error("--frame-trace requires --input-action or --input-scenario")
    args.input_scenario_payload = None
    if args.input_scenario is not None:
        try:
            args.input_scenario_payload = load_scenario(args.input_scenario)
        except ValueError as error:
            parser.error(str(error))
    if args.traffic_stall_seconds <= 0:
        parser.error("--traffic-stall-seconds must be positive")
    if args.forced_reliable_command is not None:
        try:
            normalize_reliable_command(args.forced_reliable_command)
        except ValueError as error:
            parser.error(str(error))
    return args


def main() -> int:
    flow = NaturalMatchTrace(parse_args())
    result = flow.run()
    print(json.dumps({"outcome": flow.summary["outcome"], "summary": str(flow.summary_path)}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
