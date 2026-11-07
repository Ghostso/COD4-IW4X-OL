#!/usr/bin/env python3
"""Launch, inspect, or stop CODOL client and dedicated-role processes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import locale
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import CodolClientAccount


# The host executable is per BUILD, not per project: 3.3.3.3 ships codoMP_client_shipRetail.exe,
# and the OLfinal bring-up runs out.exe (build 1649370), which is the unpacked client without the
# shipped TenProtect/TCLS stack. CODOL_CLIENT_EXECUTABLE names it. The default keeps every existing
# 3.3.3.3 invocation byte-identical, so this cannot change the behaviour of the finished
# free-for-all flow. Note SampleLauncher matches the client by PROCESS NAME from a fixed list
# (codoMP_client_shipRetail, OL, OL2, out) -- a name outside that list breaks the stack silently.
TARGET_NAME = os.environ.get("CODOL_CLIENT_EXECUTABLE") or "codoMP_client_shipRetail.exe"
TARGET_ARGUMENTS = ["-q", "0", "-src=tgp", "-game_id", "29", "-zone_id", "83886082"]
STUN_LITERAL_OFFSET = 0x181590
PATCHED_STUN_LITERAL = b"stun\0\0"
AYRIA_MODULES = (
    "Bootstrapper32.dll",
    "Localnetworking.Ayria32",
    "Platformwrapper.Ayria32",
    "Alwaysoffline.Localnet32",
    "CodolGameServer.Localnet32",
)
OPTIONAL_MODULES: tuple[str, ...] = ()
PROCESS_STATE_SCHEMA = 3
DEFAULT_DEDICATED_CONTROL_PORT = 28961
DEFAULT_CLIENT_BRIDGE_PORT = 28962
DEFAULT_ROOM_OWNER_PORT = 28970
ROOM_OWNER_NAME = "ol_room_owner.exe"


def configured_game_directory(repository: Path) -> Path | None:
    """`config/codol-game-dir.txt`, which until 2026-08-30 NOTHING read.

    The file has been in the tree, and in the README, as the machine-local game path all along --
    it is even marked skip-worktree so a checkout cannot clobber it -- but no tool ever opened it,
    so the path it names was decorative and every caller had to pass `--game-dir` by hand.
    """
    path = repository / "config" / "codol-game-dir.txt"
    try:
        text = path.read_text(encoding="utf-8-sig").strip()
    except OSError:
        return None
    if not text:
        return None
    candidate = Path(text)
    return candidate if (candidate / TARGET_NAME).is_file() else None


def find_game_directory(workspace: Path) -> Path | None:
    """Locate the game directory by CONTENT, not by folder name.

    The original matched a directory whose name starts with "Call of Duty Online " one level under
    the repository's parent. That is a layout, not a fact about the install: with both repos under
    `<game>\\servers\\` the repository's parent IS `servers`, which contains no such directory, so
    resolution returned None and `--game-dir` became mandatory. An install is identified by holding
    the client executable, so test for that and walk UP from the repository as well as down from
    the workspace -- the game directory is an ancestor in the `servers\\` layout.
    """
    repository = Path(__file__).resolve().parents[2]

    explicit = configured_game_directory(repository)
    if explicit is not None:
        return explicit

    # Walk up: `<game>/servers/ol-mod-olfinal/...` puts the install two levels above the repository.
    for ancestor in repository.parents:
        if (ancestor / TARGET_NAME).is_file():
            return ancestor

    # Then the original shape, kept so existing side-by-side checkouts resolve exactly as before.
    try:
        roots = list(workspace.iterdir())
    except OSError:
        return None
    for root in roots:
        if not root.is_dir():
            continue
        if (root / TARGET_NAME).is_file():
            return root
        if not root.name.startswith("Call of Duty Online "):
            continue
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for candidate in children:
            if candidate.is_dir() and (candidate / TARGET_NAME).is_file():
                return candidate
    return None


def running_pids() -> list[int]:
    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {TARGET_NAME}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    pids: list[int] = []
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) >= 2 and row[0].casefold() == TARGET_NAME.casefold():
            try:
                pids.append(int(row[1].replace(",", "")))
            except ValueError:
                pass
    return sorted(pids)


def process_image_name(pid: int) -> str | None:
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) >= 2 and row[1].replace(",", "").strip() == str(pid):
            return row[0]
    return None


def loaded_modules(pid: int) -> set[str] | None:
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    powershell = system_root / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not powershell.is_file():
        powershell = Path("powershell")
    command = (
        f"$p=Get-Process -Id {pid} -ErrorAction Stop; "
        "$p.Modules | ForEach-Object { $_.ModuleName }"
    )
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    if result.returncode != 0:
        return None
    return {line.strip().casefold() for line in result.stdout.splitlines() if line.strip()}


def process_state_path(game_directory: Path) -> Path:
    return game_directory / "Ayria" / "Logs" / "ol-mod-processes.json"


def read_process_state(game_directory: Path) -> dict[str, object] | None:
    path = process_state_path(game_directory)
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if (
        not isinstance(document, dict)
        or document.get("schemaVersion") not in {1, 2, PROCESS_STATE_SCHEMA}
        or document.get("gameExecutable") != TARGET_NAME
        or not isinstance(document.get("processes"), list)
    ):
        return None
    return document


def write_process_state(
    game_directory: Path,
    processes: list[dict[str, object]],
    dedicated_control_port: int,
    client_bridge_port: int,
    room_owner: dict[str, object] | None = None,
    room_owner_port: int = DEFAULT_ROOM_OWNER_PORT,
) -> None:
    path = process_state_path(game_directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schemaVersion": PROCESS_STATE_SCHEMA,
        "gameExecutable": TARGET_NAME,
        "dedicatedControlPort": dedicated_control_port,
        "clientBridgePort": client_bridge_port,
        "roomOwnerPort": room_owner_port,
        "processes": processes,
    }
    if room_owner is not None:
        document["roomOwner"] = room_owner
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def role_pids(game_directory: Path, role: str) -> list[int]:
    active = set(running_pids())
    state = read_process_state(game_directory)
    if state:
        result = []
        tracked_active = set()
        for entry in state["processes"]:
            if not isinstance(entry, dict):
                continue
            pid = entry.get("pid")
            if isinstance(pid, int) and pid in active:
                tracked_active.add(pid)
            if entry.get("role") == role and isinstance(pid, int) and pid in active:
                result.append(pid)
        if result:
            return sorted(result)
        if role == "client":
            for entry in state["processes"]:
                if not isinstance(entry, dict) or entry.get("role") != "combined":
                    continue
                pid = entry.get("pid")
                if isinstance(pid, int) and pid in active:
                    return [pid]
        if tracked_active:
            return []
    if role == "client" and len(active) == 1:
        return sorted(active)
    return []


def print_status(game_directory: Path | None = None) -> bool:
    pids = running_pids()
    if not pids:
        print(f"CODOL is not running ({TARGET_NAME}).")
        return False

    roles: dict[int, str] = {}
    if game_directory:
        state = read_process_state(game_directory)
        if state:
            for entry in state["processes"]:
                if isinstance(entry, dict) and isinstance(entry.get("pid"), int):
                    roles[entry["pid"]] = str(entry.get("role", "unknown"))
    print(f"CODOL is running. PID(s): {', '.join(map(str, pids))}")
    for pid in pids:
        print(f"Process {pid} role: {roles.get(pid, 'untracked')}")
        modules = loaded_modules(pid)
        print(f"Ayria modules in PID {pid}:")
        for name in AYRIA_MODULES:
            if modules is None:
                state = "unknown (module query failed)"
            else:
                state = "loaded" if name.casefold() in modules else "NOT LOADED"
            print(f"  {name}: {state}")
        for name in OPTIONAL_MODULES:
            if modules is not None and name.casefold() in modules:
                print(f"  {name}: loaded (post-lobby)")
    return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def launch_arguments(mode: str, role: str = "combined") -> list[str]:
    if mode == "offline":
        arguments = list(TARGET_ARGUMENTS)
    else:
        arguments = []
    # -qa is the TCLS WinMain gate. It is NOT a role flag, and treating it as one is what this
    # function got wrong: every role starts the SAME executable through the SAME WinMain, so the
    # gate fires for all of them. Started with no arguments the process dies before the engine runs,
    # on 致命错误 "请使用腾讯游戏登录器 (TCLS 文件夹内的 Client.exe) 启动游戏". Measured on build
    # 1649370, 2026-08-30, on the `client` role -- which used to get an empty argument list and then
    # failed as "did not bind control port 28962 within 40 seconds", naming the symptom and not the
    # cause. Do NOT add more arguments: Injector32 fails with ERROR_FILE_NOT_FOUND on the argument
    # COUNT, which reads as a wrong path, and that is what `offline` mode's five-token string hits.
    arguments.append("-qa")
    return arguments


def process_environment(
    role: str,
    dedicated_control_port: int,
    client_bridge_port: int,
    client_instance: int = 1,
    platform_user_id: str | None = None,
    room_owner_port: int = DEFAULT_ROOM_OWNER_PORT,
) -> dict[str, str]:
    environment = os.environ.copy()
    environment["OLMOD_PROCESS_ROLE"] = role
    environment["OLMOD_DEDICATED_CONTROL_PORT"] = str(dedicated_control_port)
    environment["OLMOD_CLIENT_BRIDGE_PORT"] = str(client_bridge_port)
    environment["OLMOD_ROOM_OWNER_PORT"] = str(room_owner_port)
    environment["OLMOD_CONSOLE_LOG"] = "1"
    # OLMOD(claim-lobby): route lobby.codol.localhost to this process's own backend instead of the
    # C# LobbyServer, so MatchmakingService runs and can send ConfigureSession to the game server.
    # Without it QueryEndpoint reports sessionConfigured=false / bound=false and no match can start.
    # Unset it to hand the lobby back to the C# stack; nothing else depends on it.
    environment["OLMOD_CLAIM_LOBBY"] = os.environ.get("OLMOD_CLAIM_LOBBY", "1")
    environment["OLMOD_CLIENT_INSTANCE"] = str(client_instance)
    if platform_user_id is not None:
        environment["OLMOD_PLATFORM_USER_ID"] = platform_user_id
    return environment


def configured_platform_user_id(game_directory: Path) -> str | None:
    path = game_directory / "Ayria" / "Assets" / "Platformwrapper" / "Platform.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        value = document.get("platformUserId")
        return CodolClientAccount.normalize_user_id(value) if isinstance(value, str) else None
    except (OSError, ValueError):
        return None


def player_account_path(game_directory: Path, user_id: str) -> Path:
    return (
        game_directory / "Ayria" / "Assets" / "Alwaysoffline" /
        "1004" / CodolClientAccount.user_id_directory(user_id)
    )


def client_process_entry(
    pid: int, instance: int, user_id: str | None, bridge_port: int
) -> dict[str, object]:
    entry: dict[str, object] = {
        "role": "client",
        "pid": pid,
        "instance": instance,
        "bridgePort": bridge_port,
    }
    if user_id is not None:
        entry["userId"] = user_id
    return entry


def ports_available(*ports: int) -> bool:
    sockets: list[socket.socket] = []
    try:
        for port in ports:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", port))
            sockets.append(listener)
        return True
    except OSError:
        return False
    finally:
        for listener in sockets:
            listener.close()


def validate_launch_files(game_directory: Path) -> tuple[Path, Path]:
    target = game_directory / TARGET_NAME
    ayria = game_directory / "Ayria"
    injector = ayria / "Injector32.exe"
    required = (
        target,
        injector,
        ayria / "Bootstrapper32.dll",
        ayria / "Plugins" / "Localnetworking.Ayria32",
        ayria / "Plugins" / "Platformwrapper.Ayria32",
        ayria / "Plugins" / "Alwaysoffline.Localnet32",
    )
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required file(s): " + ", ".join(map(str, missing)))

    localnet = ayria / "Plugins" / "Alwaysoffline.Localnet32"
    with localnet.open("rb") as stream:
        stream.seek(STUN_LITERAL_OFFSET)
        literal = stream.read(len(PATCHED_STUN_LITERAL))
    deployment = ayria / "Backups" / "AlwaysofflineRe-deployment.json"
    runtime_manifest = ayria / "ol-mod-runtime-manifest.json"
    reconstructed = False
    if runtime_manifest.is_file():
        try:
            manifest = json.loads(runtime_manifest.read_text(encoding="utf-8-sig"))
            entry = next(
                item
                for item in manifest.get("files", [])
                if item.get("path", "").casefold()
                == "ayria/plugins/alwaysoffline.localnet32"
            )
            reconstructed = entry.get("sha256", "").upper() == sha256(localnet)
        except (OSError, StopIteration, TypeError, ValueError):
            reconstructed = False
    if not reconstructed and deployment.is_file():
        try:
            record = json.loads(deployment.read_text(encoding="utf-8"))
            reconstructed = (
                record.get("state") == "deployed"
                and record.get("deployed_sha256") == sha256(localnet)
            )
        except (OSError, ValueError):
            reconstructed = False
    candidate = Path(__file__).resolve().parents[2] / "build" / "bin" / "release" / "AlwaysofflineRe.Localnet32"
    if not reconstructed and candidate.is_file():
        reconstructed = sha256(candidate) == sha256(localnet)
    if literal != PATCHED_STUN_LITERAL and not reconstructed:
        raise RuntimeError(
            f"Neither the CODOL STUN-patched archive plugin nor a recorded "
            f"AlwaysofflineRe deployment is active in {localnet}"
        )
    return target, injector


def room_owner_path(game_directory: Path) -> Path:
    return game_directory / "Ayria" / ROOM_OWNER_NAME


def launch_room_owner(
    game_directory: Path, wait_seconds: float, room_owner_port: int
) -> int | None:
    executable = room_owner_path(game_directory)
    if not executable.is_file():
        print(f"Missing shared room owner: {executable}", file=sys.stderr)
        return None
    environment = os.environ.copy()
    environment["OLMOD_ROOM_OWNER_PORT"] = str(room_owner_port)
    try:
        process = subprocess.Popen(
            [str(executable)],
            cwd=game_directory,
            env=environment,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    except OSError as error:
        print(f"Could not start shared room owner: {error}", file=sys.stderr)
        return None
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            print(
                f"Shared room owner exited with code {process.returncode}.",
                file=sys.stderr,
            )
            return None
        if not ports_available(room_owner_port):
            return process.pid
        time.sleep(0.1)
    terminate_pids([process.pid])
    print(
        f"Shared room owner did not bind port {room_owner_port} within "
        f"{wait_seconds:g} seconds.",
        file=sys.stderr,
    )
    return None


def launch_process(
    game_directory: Path,
    target: Path,
    injector: Path,
    wait_seconds: float,
    launch_mode: str,
    role: str,
    dedicated_control_port: int,
    client_bridge_port: int,
    expected_listener_port: int | None = None,
    room_owner_port: int = DEFAULT_ROOM_OWNER_PORT,
    client_instance: int = 1,
    platform_user_id: str | None = None,
) -> int | None:
    before = set(running_pids())
    def cleanup_new_processes() -> None:
        terminate_pids(sorted(set(running_pids()) - before))

    log_path = game_directory / "Ayria" / "Logs" / "CODOLLauncher.log"
    if role != "combined":
        suffix = f"-{client_instance}" if role == "client" else ""
        log_path = log_path.with_name(f"CODOLLauncher-{role}{suffix}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    arguments = launch_arguments(launch_mode, role)
    command = [str(injector), str(target), *arguments]
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            result = subprocess.run(
                command,
                cwd=game_directory,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=process_environment(
                    role,
                    dedicated_control_port,
                    client_bridge_port,
                    client_instance=client_instance,
                    platform_user_id=platform_user_id,
                    room_owner_port=room_owner_port,
                ),
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"Could not run the Ayria injector: {error}", file=sys.stderr)
        cleanup_new_processes()
        return None
    if result.returncode != 0:
        print(f"Injector exited with code {result.returncode}. See {log_path}", file=sys.stderr)
        cleanup_new_processes()
        return None

    deadline = time.monotonic() + wait_seconds
    pids: list[int] = []
    while time.monotonic() < deadline:
        pids = sorted(set(running_pids()) - before)
        if pids:
            break
        time.sleep(0.25)
    if not pids:
        print(f"Injector succeeded, but {TARGET_NAME} did not remain running. See {log_path}", file=sys.stderr)
        return None
    if len(pids) != 1:
        print(
            f"Injector created {len(pids)} new {TARGET_NAME} processes; refusing an ambiguous role assignment.",
            file=sys.stderr,
        )
        terminate_pids(pids)
        return None
    pid = pids[0]

    module_deadline = time.monotonic() + min(wait_seconds, 10.0)
    modules: set[str] | None = None
    while time.monotonic() < module_deadline:
        modules = loaded_modules(pid)
        if modules is not None and all(name.casefold() in modules for name in AYRIA_MODULES):
            break
        time.sleep(0.5)

    print(f"Launched CODOL role={role} PID={pid} through: {injector}")
    print(f"Arguments: {' '.join(arguments) if arguments else '<none>'}")
    if modules is None or not all(name.casefold() in modules for name in AYRIA_MODULES):
        print("CODOL started, but the complete Ayria module chain was not observed.", file=sys.stderr)
        terminate_pids([pid])
        return None
    if expected_listener_port is not None:
        listener_deadline = time.monotonic() + wait_seconds
        while time.monotonic() < listener_deadline:
            if pid not in running_pids():
                print(
                    f"CODOL role={role} exited before control port "
                    f"{expected_listener_port} became ready.",
                    file=sys.stderr,
                )
                return None
            if not ports_available(expected_listener_port):
                break
            time.sleep(0.25)
        else:
            print(
                f"CODOL role={role} did not bind control port "
                f"{expected_listener_port} within {wait_seconds:g} seconds.",
                file=sys.stderr,
            )
            terminate_pids([pid])
            return None
    return pid


def terminate_pids(pids: list[int]) -> list[int]:
    failed: list[int] = []
    for pid in pids:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
        if result.returncode != 0:
            failed.append(pid)
    return failed


def launch(
    game_directory: Path,
    wait_seconds: float,
    launch_mode: str,
    dedicated_control_port: int = DEFAULT_DEDICATED_CONTROL_PORT,
    client_bridge_port: int = DEFAULT_CLIENT_BRIDGE_PORT,
) -> int:
    if running_pids():
        print("Refusing to launch a second CODOL instance.", file=sys.stderr)
        print_status(game_directory)
        return 2
    if dedicated_control_port == client_bridge_port or not ports_available(
        dedicated_control_port, client_bridge_port
    ):
        print("ol-mod control ports must be distinct and available.", file=sys.stderr)
        return 2
    try:
        target, injector = validate_launch_files(game_directory)
    except (OSError, RuntimeError) as error:
        print(f"Launch validation failed: {error}", file=sys.stderr)
        return 2
    pid = launch_process(
        game_directory,
        target,
        injector,
        wait_seconds,
        launch_mode,
        "combined",
        dedicated_control_port,
        client_bridge_port,
    )
    if pid is None:
        return 3
    try:
        write_process_state(game_directory, [{"role": "combined", "pid": pid}],
            dedicated_control_port, client_bridge_port)
    except OSError as error:
        terminate_pids([pid])
        print(f"Could not persist the process role state: {error}", file=sys.stderr)
        return 3
    print_status(game_directory)
    return 0


def launch_dedicated_pair(
    game_directory: Path,
    wait_seconds: float,
    launch_mode: str,
    dedicated_control_port: int,
    client_bridge_port: int,
    room_owner_port: int = DEFAULT_ROOM_OWNER_PORT,
) -> int:
    if running_pids():
        print("Refusing to launch a dedicated pair while CODOL is already running.", file=sys.stderr)
        print_status(game_directory)
        return 2
    if len({dedicated_control_port, client_bridge_port, room_owner_port}) != 3 or not ports_available(
        dedicated_control_port, client_bridge_port, room_owner_port
    ):
        print("Dedicated and client bridge ports must be distinct and available.", file=sys.stderr)
        return 2
    try:
        target, injector = validate_launch_files(game_directory)
    except (OSError, RuntimeError) as error:
        print(f"Launch validation failed: {error}", file=sys.stderr)
        return 2

    room_owner_pid = launch_room_owner(
        game_directory, wait_seconds, room_owner_port)
    if room_owner_pid is None:
        return 3

    # Each role retains CODOL's native single-instance check. The dedicated
    # process uses a separate verified mutex name, so either role can restart
    # without weakening the normal client's singleton protection.
    primary_user_id = configured_platform_user_id(game_directory)
    client_pid = launch_process(
        game_directory, target, injector, wait_seconds, launch_mode, "client",
        dedicated_control_port, client_bridge_port, client_bridge_port,
        room_owner_port)
    if client_pid is None:
        terminate_pids([room_owner_pid])
        return 3
    try:
        write_process_state(game_directory, [client_process_entry(
            client_pid, 1, primary_user_id, client_bridge_port)],
            dedicated_control_port, client_bridge_port,
            {"pid": room_owner_pid, "executable": ROOM_OWNER_NAME},
            room_owner_port)
    except OSError as error:
        terminate_pids([client_pid, room_owner_pid])
        print(f"Could not persist the client process state: {error}", file=sys.stderr)
        return 3

    dedicated_pid = launch_process(
        game_directory, target, injector, wait_seconds, launch_mode, "dedicated",
        dedicated_control_port, client_bridge_port, dedicated_control_port,
        room_owner_port)
    if dedicated_pid is None:
        terminate_pids([client_pid, room_owner_pid])
        process_state_path(game_directory).unlink(missing_ok=True)
        return 3
    try:
        write_process_state(game_directory, [
            {"role": "dedicated", "pid": dedicated_pid},
            client_process_entry(client_pid, 1, primary_user_id, client_bridge_port),
        ], dedicated_control_port, client_bridge_port,
            {"pid": room_owner_pid, "executable": ROOM_OWNER_NAME},
            room_owner_port)
    except OSError as error:
        terminate_pids([dedicated_pid, client_pid, room_owner_pid])
        process_state_path(game_directory).unlink(missing_ok=True)
        print(f"Could not persist the dedicated pair state: {error}", file=sys.stderr)
        return 3
    print_status(game_directory)
    return 0


def launch_dedicated_two_clients(
    game_directory: Path,
    wait_seconds: float,
    launch_mode: str,
    dedicated_control_port: int,
    client_bridge_port: int,
    room_owner_port: int,
    secondary_user_id: str,
) -> int:
    """Start one dedicated process and two independently identified clients."""
    result = launch_dedicated_pair(
        game_directory,
        wait_seconds,
        launch_mode,
        dedicated_control_port,
        client_bridge_port,
        room_owner_port,
    )
    if result != 0:
        return result
    secondary_result = launch_client_for_dedicated(
        game_directory,
        wait_seconds,
        launch_mode,
        client_instance=2,
        platform_user_id=secondary_user_id,
        requested_bridge_port=client_bridge_port + 1,
    )
    if secondary_result != 0:
        # The helper owns only the process set it just launched; stopping here
        # avoids leaving a misleading one-client dedicated state behind.
        stop(game_directory)
    return secondary_result


def launch_client_for_dedicated(
    game_directory: Path,
    wait_seconds: float,
    launch_mode: str,
    client_instance: int = 1,
    platform_user_id: str | None = None,
    requested_bridge_port: int | None = None,
) -> int:
    state = read_process_state(game_directory)
    active = set(running_pids())
    if not state:
        print("A valid dedicated process-state file is required.", file=sys.stderr)
        return 2
    tracked = {
        entry.get("pid")
        for entry in state["processes"]
        if isinstance(entry, dict) and isinstance(entry.get("pid"), int)
    }
    dedicated = [
        entry["pid"]
        for entry in state["processes"]
        if isinstance(entry, dict)
        and entry.get("role") == "dedicated"
        and isinstance(entry.get("pid"), int)
        and entry["pid"] in active
    ]
    clients = [
        entry
        for entry in state["processes"]
        if isinstance(entry, dict)
        and entry.get("role") in {"client", "combined"}
        and isinstance(entry.get("pid"), int)
        and entry["pid"] in active
    ]
    active_client_pids = {
        entry["pid"] for entry in clients if entry["pid"] in active
    }
    if len(dedicated) != 1 or active != {dedicated[0], *active_client_pids} or active - tracked:
        print(
            "Refusing client recovery without one unambiguous tracked dedicated process.",
            file=sys.stderr,
        )
        print_status(game_directory)
        return 2
    dedicated_control_port = state.get("dedicatedControlPort")
    legacy_bridge_port = state.get("clientBridgePort")
    client_bridge_port = requested_bridge_port or legacy_bridge_port
    room_owner_port = state.get("roomOwnerPort", DEFAULT_ROOM_OWNER_PORT)
    room_owner = state.get("roomOwner")
    if not isinstance(dedicated_control_port, int) or not isinstance(
        client_bridge_port, int
    ) or not isinstance(room_owner_port, int
    ):
        print("Dedicated process-state ports are invalid.", file=sys.stderr)
        return 2
    room_owner_pid = room_owner.get("pid") if isinstance(room_owner, dict) else None
    room_owner_image = (
        process_image_name(room_owner_pid)
        if isinstance(room_owner_pid, int)
        else None
    )
    if (
        ports_available(dedicated_control_port)
        or not ports_available(client_bridge_port)
        or not isinstance(room_owner_pid, int)
        or not room_owner_image
        or room_owner_image.casefold() != ROOM_OWNER_NAME.casefold()
        or ports_available(room_owner_port)
    ):
        print(
            "Dedicated control must be bound and the client bridge port available.",
            file=sys.stderr,
        )
        return 2
    if not 1 <= client_instance <= 9:
        print("Client instance must be in the range 1..9.", file=sys.stderr)
        return 2
    if platform_user_id is not None:
        try:
            platform_user_id = CodolClientAccount.normalize_user_id(platform_user_id)
        except ValueError as error:
            print(f"Invalid platform user ID: {error}", file=sys.stderr)
            return 2
    elif client_instance == 1:
        platform_user_id = configured_platform_user_id(game_directory)
    existing_clients = [entry for entry in clients if entry["pid"] in active]
    if client_instance > 1 and any(
        not isinstance(entry.get("instance"), int)
        or not isinstance(entry.get("userId"), str)
        or not isinstance(entry.get("bridgePort"), int)
        for entry in existing_clients
    ):
        print(
            "Existing clients lack schema-3 identity metadata; restart the dedicated set.",
            file=sys.stderr,
        )
        return 2
    existing_instances = {
        entry.get("instance", 1) for entry in existing_clients
    }
    existing_users = {
        str(entry["userId"]).casefold()
        for entry in existing_clients if isinstance(entry.get("userId"), str)
    }
    existing_ports = {
        entry.get("bridgePort", legacy_bridge_port) for entry in existing_clients
    }
    if (client_instance in existing_instances or
        (platform_user_id is not None and platform_user_id.casefold() in existing_users) or
        client_bridge_port in existing_ports):
        print("Client instance, user ID, and bridge port must be unique.", file=sys.stderr)
        return 2
    if client_instance > 1 and platform_user_id is None:
        print("Secondary clients require --platform-user-id.", file=sys.stderr)
        return 2
    if client_instance > 1 and platform_user_id is not None:
        account = player_account_path(game_directory, platform_user_id)
        if not account.is_dir() or not (account / "Identity.json").is_file():
            print(
                f"Secondary client account is not seeded: {account}",
                file=sys.stderr,
            )
            return 2
    try:
        target, injector = validate_launch_files(game_directory)
    except (OSError, RuntimeError) as error:
        print(f"Launch validation failed: {error}", file=sys.stderr)
        return 2
    client_pid = launch_process(
        game_directory,
        target,
        injector,
        wait_seconds,
        launch_mode,
        "client",
        dedicated_control_port,
        client_bridge_port,
        client_bridge_port,
        room_owner_port,
        client_instance,
        platform_user_id,
    )
    if client_pid is None:
        return 3
    try:
        write_process_state(
            game_directory,
            [
                {"role": "dedicated", "pid": dedicated[0]},
                *existing_clients,
                client_process_entry(
                    client_pid, client_instance, platform_user_id, client_bridge_port),
            ],
            dedicated_control_port,
            legacy_bridge_port,
            {"pid": room_owner_pid, "executable": ROOM_OWNER_NAME},
            room_owner_port,
        )
    except OSError as error:
        terminate_pids([client_pid])
        print(f"Could not persist the recovered client role: {error}", file=sys.stderr)
        return 3
    print_status(game_directory)
    return 0


def stop(game_directory: Path | None = None) -> int:
    pids = running_pids()
    room_owner_pid: int | None = None
    if game_directory:
        state = read_process_state(game_directory)
        room_owner = state.get("roomOwner") if state else None
        if isinstance(room_owner, dict) and isinstance(room_owner.get("pid"), int):
            candidate = room_owner["pid"]
            image = process_image_name(candidate)
            if image and image.casefold() == ROOM_OWNER_NAME.casefold():
                room_owner_pid = candidate
    if not pids and room_owner_pid is None:
        if game_directory:
            process_state_path(game_directory).unlink(missing_ok=True)
        print(f"CODOL is not running ({TARGET_NAME}).")
        return 0

    stopped = [*pids]
    if room_owner_pid is not None:
        stopped.append(room_owner_pid)
    failed = terminate_pids(stopped)

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and running_pids():
        time.sleep(0.2)
    remaining = running_pids()
    failed = sorted(set(failed + remaining))
    if failed:
        print(f"Could not stop PID(s): {', '.join(map(str, failed))}", file=sys.stderr)
        return 3
    if game_directory:
        process_state_path(game_directory).unlink(missing_ok=True)
    print(f"Stopped ol-mod PID(s): {', '.join(map(str, stopped))}")
    return 0


def launch_with_inventory(
    repository: Path,
    game_directory: Path,
    wait_seconds: float,
    inventory_timeout: float,
    launch_mode: str,
) -> int:
    del repository, inventory_timeout
    print(
        "launch-inventory is a compatibility alias; ol_backend now loads "
        "with the normal Localnetworking startup chain."
    )
    return launch(game_directory, wait_seconds, launch_mode)


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "launch", "launch-dedicated", "launch-dedicated-two", "launch-client",
            "launch-inventory", "status", "stop",
        ),
    )
    parser.add_argument("--game-dir", type=Path, default=find_game_directory(repository.parent))
    parser.add_argument("--wait", type=float, default=20.0, help="Seconds to wait after launching")
    parser.add_argument("--inventory-timeout", type=float, default=90.0)
    parser.add_argument(
        "--dedicated-control-port", type=int, default=DEFAULT_DEDICATED_CONTROL_PORT)
    parser.add_argument(
        "--client-bridge-port", type=int)
    parser.add_argument(
        "--room-owner-port", type=int, default=DEFAULT_ROOM_OWNER_PORT)
    parser.add_argument("--client-instance", type=int, default=1)
    parser.add_argument("--platform-user-id")
    parser.add_argument(
        "--secondary-user-id", default="01100001DEADC0DF",
        help="XUID for the second client in launch-dedicated-two")
    parser.add_argument(
        "--launch-mode",
        choices=("auto", "no-args", "offline"),
        default="auto",
        help="auto and no-args match drag-and-drop injection; offline explicitly adds OfflineLauncher arguments",
    )
    parser.set_defaults(repository=repository)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.game_dir is None:
        print("Could not locate the CODOL game directory; pass --game-dir.", file=sys.stderr)
        return 2
    game_directory = args.game_dir.resolve()
    if not (1 <= args.dedicated_control_port <= 65535) or (
        args.client_bridge_port is not None and
        not 1 <= args.client_bridge_port <= 65535
    ) or not (1 <= args.room_owner_port <= 65535
    ):
        print("Control ports must be in the range 1..65535.", file=sys.stderr)
        return 2
    if args.action == "launch":
        return launch(
            game_directory,
            args.wait,
            args.launch_mode,
            args.dedicated_control_port,
            args.client_bridge_port or DEFAULT_CLIENT_BRIDGE_PORT,
        )
    if args.action == "launch-dedicated":
        return launch_dedicated_pair(
            game_directory,
            args.wait,
            args.launch_mode,
            args.dedicated_control_port,
            args.client_bridge_port or DEFAULT_CLIENT_BRIDGE_PORT,
            args.room_owner_port,
        )
    if args.action == "launch-dedicated-two":
        return launch_dedicated_two_clients(
            game_directory,
            args.wait,
            args.launch_mode,
            args.dedicated_control_port,
            args.client_bridge_port or DEFAULT_CLIENT_BRIDGE_PORT,
            args.room_owner_port,
            args.secondary_user_id,
        )
    if args.action == "launch-client":
        return launch_client_for_dedicated(
            game_directory,
            args.wait,
            args.launch_mode,
            args.client_instance,
            args.platform_user_id,
            args.client_bridge_port,
        )
    if args.action == "launch-inventory":
        return launch_with_inventory(
            args.repository,
            game_directory,
            args.wait,
            args.inventory_timeout,
            args.launch_mode,
        )
    if args.action == "stop":
        return stop(game_directory)
    return 0 if print_status(game_directory) else 1


if __name__ == "__main__":
    raise SystemExit(main())
