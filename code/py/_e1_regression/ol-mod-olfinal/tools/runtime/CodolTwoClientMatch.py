#!/usr/bin/env python3
"""Drive two real CODOL clients through one shared room, then book once.

This is an orchestration tool, not a second matchmaking implementation.  It
only calls CodolMatchFlow and uses the standalone room-owner log as the
authoritative gate before asking the owner client to allocate.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from CodolDedicatedStatus import decode as decode_dedicated_status
from CodolDedicatedStatus import submit as submit_dedicated_status


ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / "tools" / "runtime" / "CodolMatchFlow.py"
ROOM_STATE_RE = re.compile(
    r"\[room-owner\] (?P<event>connect|disconnect|ready|unready|freeze) "
    r".* members=(?P<members>\d+) ready=(?P<ready>\d+) accepted=(?P<accepted>[01])"
)
SESSION_ACCEPTED = "CODOL_GAME_SESSION accepted=true"
SESSION_QUEUED_RE = re.compile(
    r"SessionStart queued request=(?P<request>\d+) .* members=(?P<members>\d+)"
)
SESSION_ACCEPTED_RE = re.compile(
    r"SessionStart accepted request=(?P<request>\d+)"
)
RUNTIME_RE = re.compile(r"runtime clients=(?P<clients>\d+) active=(?P<active>\d+)")
PLAYING_SLOT_RE = re.compile(
    r"client-slot (?P<slot>\d+).*gameplay=2 .*\bloadout_seq=(?P<seq>\d+)"
)


def read_log_delta(log: Path, position: int) -> tuple[str, int]:
    """Read appended lines and recover if the owner/server rewrote its log."""
    try:
        size = log.stat().st_size
        if size < position:
            position = 0
        with log.open("r", encoding="utf-8", errors="replace") as stream:
            stream.seek(position)
            chunk = stream.read()
            return chunk, stream.tell()
    except OSError:
        return "", position


def run_flow(pid: int, action: str, args: argparse.Namespace) -> None:
    command = [
        sys.executable, str(FLOW), "--pid", str(pid), "--action", action,
        "--timeout", str(args.client_timeout),
    ]
    if action in {"match", "full"}:
        # The playlist id is what actually decides the booking; map and mode alone
        # leave CodolMatchFlow on its default of 26, which is why asking for a
        # free-for-all map and mode still produced a search-and-destroy match.
        command += [
            "--map", args.map,
            "--mode", args.mode,
            "--playlist-id", str(args.playlist_id),
        ]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(f"client {pid} action {action} failed ({result.returncode})")


def run_parallel(pids: list[int], action: str, args: argparse.Namespace) -> None:
    # QuickMatch must be submitted by both native clients before either one
    # observes the shared room as active.  Serialising this step makes the
    # second client reject its own already-active room instead of joining it.
    with ThreadPoolExecutor(max_workers=len(pids)) as pool:
        futures = [pool.submit(run_flow, pid, action, args) for pid in pids]
        for future in futures:
            future.result()


def run_forward_probe(pids: list[int], args: argparse.Namespace) -> None:
    """Exercise the native forward path on every tracked client once.

    This is deliberately opt-in: matchmaking orchestration should not inject
    input unless the caller requests a gameplay smoke test.
    """
    output_dir = (ROOT / ".runtime" / "two-client-input").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    input_tool = ROOT / "tools" / "runtime" / "CodolClientInput.py"

    def run_one(index_pid: tuple[int, int]) -> tuple[int, subprocess.CompletedProcess[str]]:
        index, pid = index_pid
        output = output_dir / f"client-{index}-{pid}.json"
        command = [
            sys.executable, str(input_tool), "forward", "--pid", str(pid),
            "--local-client", "0", "--hold-seconds", str(args.forward_hold),
            "--observe-seconds", str(args.forward_observe), "--timeout",
            str(args.client_timeout), "--sample-interval",
            str(args.forward_sample_interval), "--no-parser-trace",
            "--output", str(output),
        ]
        return index, subprocess.run(
            command, cwd=ROOT, check=False, capture_output=True, text=True,
        )

    with ThreadPoolExecutor(max_workers=len(pids)) as pool:
        results = list(pool.map(run_one, enumerate(pids)))
    failed = []
    for index, result in results:
        if result.returncode != 0:
            failed.append(f"client {index} input probe exited {result.returncode}")
            continue
        try:
            evidence = json.loads(
                (output_dir / f"client-{index}-{pids[index]}.json")
                .read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            failed.append(f"client {index} input probe output invalid: {error}")
            continue
        parser = evidence.get("parser_summary", {})
        parser_trace = bool(evidence.get("parser_trace", False))
        if (
            evidence.get("ok") is not True
            or (parser_trace and parser.get("accepted_packet_count", 0) <= 0)
            or evidence.get("process_alive_after_observation") is not True
        ):
            failed.append(
                f"client {index} input probe did not close cleanly: "
                f"{json.dumps(evidence, ensure_ascii=False)[:400]}"
            )
        elif parser_trace and (
            parser.get("rejected_packet_count", 0) != 0
            or parser.get("overflow_events", 0) != 0
        ):
            failed.append(
                f"client {index} parser trace observed rejects/overflow: "
                f"{json.dumps(parser, ensure_ascii=False)[:300]}"
            )
    if failed:
        raise SystemExit("; ".join(failed))
    print(
        "two-client forward probe passed for "
        f"{len(pids)} tracked clients; evidence={output_dir}"
    )


def process_state(game: Path) -> list[int]:
    state_path = game / "Ayria" / "Logs" / "ol-mod-processes.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    clients = [
        entry for entry in state["processes"]
        if entry.get("role") == "client"
        and isinstance(entry.get("pid"), int)
    ]
    if len(clients) != 2:
        raise SystemExit(
            f"expected exactly two tracked clients, found {len(clients)}"
        )
    instances = {entry.get("instance") for entry in clients}
    if instances != {1, 2}:
        raise SystemExit(
            "two-client process state must contain unique instances 1 and 2"
        )
    # Instance 1 owns native room creation and dedicated allocation. PID
    # ordering is random across launches and must never determine role order.
    return [entry["pid"] for entry in sorted(
        clients, key=lambda entry: entry["instance"]
    )]


def wait_for_room_member_count(
    log: Path, timeout: float, start_size: int, expected: int
) -> None:
    deadline = time.monotonic() + timeout
    position = start_size
    carry = ""
    while time.monotonic() < deadline:
        chunk, position = read_log_delta(log, position)
        chunk = carry + chunk
        complete, carry = chunk.rsplit("\n", 1) if "\n" in chunk else ("", chunk)
        latest_members = None
        for match in ROOM_STATE_RE.finditer(complete):
            if match.group("accepted") == "1":
                latest_members = int(match.group("members"))
        if latest_members == expected:
            return
        time.sleep(0.25)
    raise SystemExit(
        f"room owner never observed {expected} connected client(s)"
    )


def wait_for_room_members(log: Path, timeout: float, start_size: int) -> None:
    wait_for_room_member_count(log, timeout, start_size, 2)


def wait_for_two_ready(log: Path, timeout: float, start_size: int) -> None:
    deadline = time.monotonic() + timeout
    position = start_size
    carry = ""
    while time.monotonic() < deadline:
        chunk, position = read_log_delta(log, position)
        chunk = carry + chunk
        complete, carry = chunk.rsplit("\n", 1) if "\n" in chunk else ("", chunk)
        latest = None
        for match in ROOM_STATE_RE.finditer(complete):
            if match.group("accepted") == "1":
                latest = (int(match.group("members")), int(match.group("ready")))
        if latest == (2, 2):
            return
        time.sleep(0.25)
    raise SystemExit("room owner never observed members=2 ready=2")


def wait_for_room_frozen(log: Path, timeout: float, start_size: int) -> None:
    deadline = time.monotonic() + timeout
    position = start_size
    carry = ""
    while time.monotonic() < deadline:
        chunk, position = read_log_delta(log, position)
        chunk = carry + chunk
        complete, carry = chunk.rsplit("\n", 1) if "\n" in chunk else ("", chunk)
        for match in ROOM_STATE_RE.finditer(complete):
            if (match.group("event") == "freeze"
                    and match.group("accepted") == "1"
                    and (int(match.group("members")), int(match.group("ready"))) == (2, 2)):
                return
        time.sleep(0.25)
    raise SystemExit("room owner never froze members=2 ready=2")


def wait_for_session_ready(log: Path, timeout: float, start_size: int) -> bool:
    deadline = time.monotonic() + timeout
    position = start_size
    carry = ""
    queued_request = None
    accepted_request = None
    last_runtime = None
    while time.monotonic() < deadline:
        chunk, position = read_log_delta(log, position)
        chunk = carry + chunk
        complete, carry = chunk.rsplit("\n", 1) if "\n" in chunk else ("", chunk)
        for line in complete.splitlines():
            queued = SESSION_QUEUED_RE.search(line)
            if queued and int(queued.group("members")) == 2:
                queued_request = int(queued.group("request"))
            accepted = SESSION_ACCEPTED_RE.search(line)
            if accepted:
                accepted_request = int(accepted.group("request"))
            runtime = RUNTIME_RE.search(line)
            if runtime:
                last_runtime = (
                    int(runtime.group("clients")),
                    int(runtime.group("active")),
                )
            # A connected slot is not yet a usable gameplay client.  Require
            # both slots to become active and at least one snapshot to have
            # been emitted; this prevents a short-lived handshake from being
            # reported as a successful two-client match.
            if (queued_request is not None and accepted_request == queued_request
                    and runtime and int(runtime.group("clients")) == 2
                    and int(runtime.group("active")) >= 2
                    and _snapshot_count(line) > 0):
                return True
        time.sleep(0.25)
    if last_runtime is not None:
        print(
            "dedicated session timeout: "
            f"runtime clients={last_runtime[0]} active={last_runtime[1]}",
        )
    return False


def submit_loadouts(
    pids: list[int], loadout: str, *, same_team: bool = False
) -> None:
    """Submit native loadouts, splitting the two clients for SD by default."""
    command_tool = ROOT / "tools" / "runtime" / "CodolClientCommand.py"
    for index, pid in enumerate(pids):
        # CODOL's script menus are changeclass_marines=1 and
        # changeclass_opfor=2.  A split is required to exercise SD's
        # team-filtered objectives and bomb ownership.  Keep same-team mode
        # for transport-only regressions.
        menu_index = 1 if same_team or index == 0 else 2
        result = subprocess.run(
            [sys.executable, str(command_tool),
             f"mr 0 {menu_index} {loadout}",
             "--pid", str(pid)],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
        if result.returncode != 0:
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            raise SystemExit(
                f"client {pid} loadout response failed ({result.returncode}): "
                f"stdout={stdout[:2000]!r} stderr={stderr[:2000]!r}"
            )


def wait_for_playing(
    timeout: float, backend_log: Path, start_size: int
) -> dict:
    """Wait until every connected slot has an atomically committed loadout.

    The dedicated log is the natural server-side evidence boundary.  Do not
    poll CodolGameServerControl here: each invocation attaches Frida to the
    game-server process, and repeated attach/detach can terminate it.
    """
    deadline = time.monotonic() + timeout
    log_position = start_size
    log_carry = ""
    log_playing_slots: set[int] = set()
    log_loadout_slots: set[int] = set()
    while time.monotonic() < deadline:
        if backend_log.exists():
            chunk, log_position = read_log_delta(backend_log, log_position)
            chunk = log_carry + chunk
            complete, log_carry = (
                chunk.rsplit("\n", 1) if "\n" in chunk else ("", chunk)
            )
            for line in complete.splitlines():
                slot = PLAYING_SLOT_RE.search(line)
                if slot and int(slot.group("seq")) > 0:
                    client_slot = int(slot.group("slot"))
                    log_playing_slots.add(client_slot)
                    log_loadout_slots.add(client_slot)
            if log_playing_slots.issuperset({0, 1}) and log_loadout_slots.issuperset({0, 1}):
                return {"evidence": "dedicated-log", "playing_slots": sorted(log_playing_slots)}
        time.sleep(0.25)
    raise SystemExit(
        "dedicated log did not confirm both clients in Playing after loadout response"
    )


def transport_progress_counters(transport: dict[str, int]) -> dict[str, int]:
    """Return counters that must progress while a client remains in Playing."""
    # message_acknowledge is not a heartbeat. It may legitimately remain fixed
    # until the client receives a newer server message, while snapshots and
    # usercmd packets continue normally. Reliable command health is checked by
    # the explicit sequence/acknowledge backlog gate below.
    return {
        "incoming_sequence": transport["incoming_sequence"],
        "udp_send_succeeded": transport["udp_send_succeeded"],
    }


def verify_transport_stability(args: argparse.Namespace) -> Path:
    """Require transport, command execution, and player projection to stay healthy."""
    output_dir = ROOT / ".runtime" / "two-client-stability"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / time.strftime("%Y%m%d-%H%M%S.jsonl")
    deadline = time.monotonic() + args.stability_seconds
    baseline: dict[int, dict[str, int]] = {}
    last_progress: dict[tuple[int, str], float] = {}
    reliable_backlog_since: dict[int, float] = {}
    usercmd_backlog_since: dict[int, float] = {}
    sample_count = 0
    first_sample_wall_time: float | None = None
    first_server_time: int | None = None
    last_sample_wall_time: float | None = None
    last_server_time: int | None = None

    with output.open("w", encoding="utf-8") as stream:
        while True:
            last_error = None
            for attempt in range(3):
                try:
                    status = decode_dedicated_status(submit_dedicated_status(
                        args.control_host, args.control_port,
                        args.control_timeout,
                    ))
                    break
                except (OSError, RuntimeError) as error:
                    last_error = error
                    if attempt < 2:
                        time.sleep(0.1)
            else:
                raise SystemExit(
                    "dedicated status query failed after three attempts: "
                    f"{last_error}; evidence={output}"
                )
            now = time.monotonic()
            if first_sample_wall_time is None:
                first_sample_wall_time = now
                first_server_time = status["server_time"]
            last_sample_wall_time = now
            last_server_time = status["server_time"]
            stream.write(json.dumps(
                status, ensure_ascii=False, separators=(",", ":")
            ) + "\n")
            stream.flush()
            sample_count += 1

            clients = {
                client["client_num"]: client for client in status["clients"]
            }
            if set(clients) != {0, 1}:
                raise SystemExit(
                    f"two-client stability lost a slot: {sorted(clients)}; "
                    f"evidence={output}"
                )
            for client_num, client in clients.items():
                if client["gameplay_state"] != 2:
                    raise SystemExit(
                        f"client {client_num} left Playing; evidence={output}"
                    )
                transport = client.get("transport")
                if transport is None:
                    raise SystemExit(
                        "dedicated does not expose schema-2 transport status; "
                        f"evidence={output}"
                    )
                if transport["udp_send_failed"]:
                    raise SystemExit(
                        f"client {client_num} UDP send failed "
                        f"count={transport['udp_send_failed']} "
                        f"error={transport['last_udp_send_error']}; evidence={output}"
                    )
                usercmd = client.get("usercmd")
                projection = client.get("snapshot_projection")
                if usercmd is None or projection is None:
                    raise SystemExit(
                        "dedicated does not expose schema-3 gameplay diagnostics; "
                        f"evidence={output}"
                    )
                expected_mask = (1 << 0) | (1 << 1)
                if (
                    projection["player_entity_mask"] & expected_mask
                ) != expected_mask or (
                    projection["client_info_mask"] & expected_mask
                ) != expected_mask:
                    raise SystemExit(
                        f"client {client_num} world projection lacks both players: "
                        f"entities=0x{projection['player_entity_mask']:08X} "
                        f"clientInfo=0x{projection['client_info_mask']:08X}; "
                        f"evidence={output}"
                    )
                received = usercmd["last_received_time"]
                executed = usercmd["last_executed_time"]
                command_lag = 0
                if received is not None and executed is not None:
                    command_lag = (received - executed) & 0xFFFFFFFF
                    if command_lag > 0x7FFFFFFF:
                        command_lag = 0
                usercmd_unhealthy = (
                    usercmd["pending_count"] > args.maximum_pending_usercmds
                    or command_lag > args.maximum_usercmd_lag_msec
                    or (received is not None and executed is None)
                )
                if usercmd_unhealthy:
                    usercmd_backlog_since.setdefault(client_num, now)
                    if now - usercmd_backlog_since[client_num] > args.usercmd_stall_seconds:
                        raise SystemExit(
                            f"client {client_num} usercmd backlog persisted: "
                            f"pending={usercmd['pending_count']} lag={command_lag}ms "
                            f"received={received} executed={executed} "
                            f"clientThink={client.get('client_think')}; "
                            f"evidence={output}"
                        )
                else:
                    usercmd_backlog_since.pop(client_num, None)
                reliable_sequence = client["server_reliable_sequence"]
                reliable_acknowledge = client["server_reliable_acknowledge"]
                if reliable_sequence > reliable_acknowledge:
                    reliable_backlog_since.setdefault(client_num, now)
                    if now - reliable_backlog_since[client_num] > args.reliable_stall_seconds:
                        raise SystemExit(
                            f"client {client_num} reliable backlog persisted at "
                            f"{reliable_acknowledge}/{reliable_sequence}; evidence={output}"
                        )
                else:
                    reliable_backlog_since.pop(client_num, None)
                values = transport_progress_counters(transport)
                if client_num not in baseline:
                    baseline[client_num] = values.copy()
                    for field in values:
                        last_progress[(client_num, field)] = now
                else:
                    for field, value in values.items():
                        key = (client_num, field)
                        if value > baseline[client_num][field]:
                            last_progress[key] = now
                            baseline[client_num][field] = value
                        if now - last_progress[key] > args.transport_stall_seconds:
                            raise SystemExit(
                                f"client {client_num} {field} stalled at {value} "
                                f"for more than {args.transport_stall_seconds:.1f}s; "
                                f"evidence={output}"
                            )
            if now >= deadline:
                break
            time.sleep(args.stability_interval)

    if sample_count < 2:
        raise SystemExit(f"transport stability window was too short; evidence={output}")
    assert first_sample_wall_time is not None and first_server_time is not None
    assert last_sample_wall_time is not None and last_server_time is not None
    observed_wall_msec = (last_sample_wall_time - first_sample_wall_time) * 1000.0
    observed_server_msec = (last_server_time - first_server_time) & 0xFFFFFFFF
    minimum_server_msec = observed_wall_msec * args.minimum_server_time_ratio
    if observed_server_msec < minimum_server_msec:
        raise SystemExit(
            "dedicated simulation clock advanced too slowly: "
            f"server={observed_server_msec}ms wall={observed_wall_msec:.0f}ms "
            f"ratio={observed_server_msec / observed_wall_msec:.3f} "
            f"minimum={args.minimum_server_time_ratio:.3f}; evidence={output}"
        )
    return output


def _snapshot_count(line: str) -> int:
    match = re.search(r"snapshots=(?P<count>\d+)", line)
    return int(match.group("count")) if match else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--map", default="mp_crash_tropical")
    parser.add_argument("--mode", default="sd")
    # Client-side playlist SLOT, not the publisher playlist id: a live client that
    # picked FREE FOR ALL by hand booked slot 11, while the shipped file calls that
    # playlist 23. 26 is the search-and-destroy slot and stays the default.
    parser.add_argument("--playlist-id", type=int, default=26)
    parser.add_argument("--client-timeout", type=float, default=45.0)
    parser.add_argument("--room-timeout", type=float, default=20.0)
    parser.add_argument(
        "--session-timeout", type=float, default=90.0,
        help="dedicated map/assets/world initialization timeout",
    )
    parser.add_argument(
        "--loadout", default="custom1",
        help="native changeclass response submitted independently to each client",
    )
    parser.add_argument(
        "--same-team", action="store_true",
        help="keep both clients on changeclass_marines (transport-only regression)",
    )
    parser.add_argument(
        "--exercise-forward", action="store_true",
        help="After booking, run a short native forward probe on both clients",
    )
    parser.add_argument("--forward-hold", type=float, default=0.8)
    parser.add_argument("--forward-observe", type=float, default=1.2)
    parser.add_argument(
        "--forward-sample-interval", type=float, default=0.25,
        help="low-interference native probe sampling period in seconds",
    )
    parser.add_argument(
        "--stability-seconds", type=float, default=60.0,
        help="seconds both natural gameplay streams must remain progressive",
    )
    parser.add_argument("--stability-interval", type=float, default=0.5)
    parser.add_argument("--transport-stall-seconds", type=float, default=5.0)
    parser.add_argument("--reliable-stall-seconds", type=float, default=12.0)
    parser.add_argument("--usercmd-stall-seconds", type=float, default=2.0)
    parser.add_argument("--maximum-pending-usercmds", type=int, default=32)
    parser.add_argument("--maximum-usercmd-lag-msec", type=int, default=500)
    parser.add_argument(
        "--minimum-server-time-ratio", type=float, default=0.8,
        help="minimum server_time progress divided by observed wall time",
    )
    parser.add_argument("--control-host", default="127.0.0.1")
    parser.add_argument("--control-port", type=int, default=28961)
    parser.add_argument("--control-timeout", type=float, default=2.0)
    parser.add_argument(
        "--verify-current", action="store_true",
        help="skip matchmaking and verify the two clients already in-game",
    )
    args = parser.parse_args()
    if (
        args.stability_seconds <= 0
        or args.stability_interval <= 0
        or args.transport_stall_seconds <= 0
        or args.reliable_stall_seconds <= 0
        or args.usercmd_stall_seconds <= 0
        or args.maximum_pending_usercmds < 0
        or args.maximum_usercmd_lag_msec < 0
        or not 0 < args.minimum_server_time_ratio <= 1
    ):
        parser.error("stability durations must be positive and backlog limits non-negative")

    clients = process_state(args.game_dir)
    if args.verify_current:
        if args.exercise_forward:
            run_forward_probe(clients, args)
        stability_evidence = verify_transport_stability(args)
        print(
            "current two-client transport remained progressive for "
            f"{args.stability_seconds:.1f}s; evidence={stability_evidence}"
        )
        return 0
    owner_log = args.game_dir / "Ayria" / "Logs" / "ol-room-owner.log"
    # SessionStart is accepted by the dedicated control endpoint, while the
    # actual two-client proof is emitted by the dedicated game-server log.
    backend_log = args.game_dir / "Ayria" / "Logs" / "CodolGameServer.log"
    start_size = owner_log.stat().st_size if owner_log.exists() else 0
    backend_start_size = backend_log.stat().st_size if backend_log.exists() else 0

    for pid in clients:
        run_flow(pid, "frontend", args)
    # Let one native client publish the discoverable room before the second
    # client runs FindSessions. Starting both QuickMatch calls concurrently
    # allows both queries to return empty and creates two independent native
    # one-player rooms even though the external owner later sees two members.
    # The first room has a native countdown, so start the second client as soon
    # as the owner observes the first RoomConnect rather than using a fixed
    # delay.
    run_flow(clients[0], "match", args)
    wait_for_room_member_count(owner_log, args.room_timeout, start_size, 1)
    run_flow(clients[1], "match", args)
    # Both native clients must have joined the shared room before either sends
    # ready. Otherwise booking can freeze a one-member roster while the second
    # client is still completing RoomConnect.
    wait_for_room_members(owner_log, args.room_timeout, start_size)
    run_parallel(clients, "ready", args)

    wait_for_two_ready(owner_log, args.room_timeout, start_size)
    wait_for_room_frozen(owner_log, args.room_timeout, start_size)
    if not wait_for_session_ready(
        backend_log, args.session_timeout, backend_start_size
    ):
        raise SystemExit("dedicated session did not reach two connected clients")
    # Start at the current end of the high-volume server log.  Reusing the
    # pre-match offset can make this gate process hundreds of megabytes of ACK
    # history and time out despite both clients already being in Playing.
    playing_start_size = backend_log.stat().st_size if backend_log.exists() else 0
    submit_loadouts(clients, args.loadout, same_team=args.same_team)
    wait_for_playing(args.session_timeout, backend_log, playing_start_size)
    print(
        "dedicated session reached Playing with independent loadouts: "
        f"clients={len(clients)} loadout={args.loadout}"
    )
    if args.exercise_forward:
        run_forward_probe(clients, args)
    stability_evidence = verify_transport_stability(args)
    print(
        "two-client natural transport remained progressive for "
        f"{args.stability_seconds:.1f}s; evidence={stability_evidence}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
