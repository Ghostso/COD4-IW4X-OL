"""Publish the local C1 player's verified match state to Discord Rich Presence.

The C1 console records the map and mode it actually joined. The local dedicated
server independently reports its running map, mode and player count. A match is
shown only when both agree and C1 reached CA_ACTIVE. No client hook is needed.
"""

from __future__ import annotations

import argparse
import ctypes
import csv
from dataclasses import dataclass
from datetime import datetime
import json
import msvcrt
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import time
import uuid


MAPS = {
    "mp_killhouse_sh": "Killhouse",
    "mp_rust": "Rust",
    "mp_nuked": "Nuketown",
    "zm_prototype_sh": "Prototype",
    "zm_asylum_sh": "Asylum",
    "zm_zombie_training": "Zombie Training",
}
MODES = {
    "combat": "Combat Training", "war": "Team Deathmatch",
    "dom": "Domination", "dm": "Free-for-All", "ctf": "Capture the Flag",
    "sd": "Search and Destroy", "sab": "Sabotage", "koth": "Headquarters",
    "oneflag": "One Flag CTF", "arena": "Arena", "dd": "Demolition",
    "vip": "VIP", "conf": "Kill Confirmed", "infect": "Infected",
    "hp": "Hardpoint", "zm": "Zombies", "coop": "Co-op",
}
TRANSITION = re.compile(r"\b(CA_[A-Z]+) -> (CA_[A-Z]+)\b")
STATUS = re.compile(
    r"\bsh1x_status map=(\S+) session_map=(\S+) gametype=(\S+) "
    r"type=(\S+) running=(\d+) humans=(\d+) bots=(\d+) maxclients=(\d+)"
)
MAX_RPC_FRAME = 16 * 1024
DEFAULT_APPLICATION_ID = "1554730441825718272"
ICON_KEY = "codol"
ICON_TEXT = "Call of Duty Online"


@dataclass(frozen=True)
class Match:
    map_name: str
    mode: str
    humans: int
    bots: int
    capacity: int


@dataclass(frozen=True)
class Activity:
    details: str
    state: str
    image: str
    image_text: str
    started_at: int


class ClientLog:
    def __init__(self, path: Path):
        self.path = path
        self.offset = 0
        self.file_id = None
        self.active = False
        self.active_since = 0
        self.map_name = ""
        self.mode = ""
        self._in_start_game = False

    def reset(self) -> None:
        self.offset = 0
        self.file_id = None
        self.active = False
        self.active_since = 0
        self.map_name = ""
        self.mode = ""
        self._in_start_game = False

    def update(self) -> None:
        try:
            stat = self.path.stat()
            file_id = (stat.st_dev, stat.st_ino)
            if self.file_id != file_id or stat.st_size < self.offset:
                self.reset()
                self.file_id = file_id
            with self.path.open("rb") as stream:
                stream.seek(self.offset)
                for raw in stream:
                    self.feed(raw.decode("utf-8", errors="replace"))
                self.offset = stream.tell()
        except OSError:
            self.reset()

    def feed(self, line: str) -> None:
        if "StartGameRecv" in line:
            self.active = False
            self.map_name = ""
            self.mode = ""
            self._in_start_game = True
        elif self._in_start_game:
            found = re.search(r"\bmap:\s+([a-z0-9_]+)", line)
            if found:
                self.map_name = found.group(1)
            found = re.search(r"\btype:\s+([a-z0-9_]+)", line)
            if found:
                self.mode = found.group(1)
                self._in_start_game = False
        if "DISCONNECTING" in line:
            self.active = False
        transition = TRANSITION.search(line)
        if transition:
            old, new = transition.groups()
            if new == "CA_ACTIVE":
                self.active = True
                stamp = re.match(r"\[([^]]+)\]", line)
                if stamp:
                    try:
                        self.active_since = int(datetime.strptime(
                            stamp.group(1).strip(), "%a %b %d %H:%M:%S %Y").timestamp())
                    except ValueError:
                        self.active_since = int(time.time())
                else:
                    self.active_since = int(time.time())
            elif old == "CA_ACTIVE" or new == "CA_DISCONNECTED":
                self.active = False


def parse_status(reply: str) -> Match | None:
    found = STATUS.search(reply)
    if not found:
        return None
    map_name, session_map, mode, zone, running, humans, bots, capacity = found.groups()
    if running != "1" or map_name != session_map or zone not in ("mp", "zm"):
        return None
    return Match(map_name, mode, int(humans), int(bots), int(capacity))


def verified_match(client: ClientLog, server: Match | None) -> Match | None:
    if (server is None or not client.active or server.humans < 1
            or client.map_name != server.map_name or client.mode != server.mode):
        return None
    return server


def activity_for(match: Match | None, started_at: int) -> Activity:
    if match is None:
        return Activity("In the lobby", "Choosing a match", ICON_KEY, ICON_TEXT, started_at)
    map_label = MAPS.get(match.map_name, match.map_name)
    mode_label = MODES.get(match.mode, match.mode.upper())
    players = f"{match.humans} player{'s' if match.humans != 1 else ''}"
    if match.bots:
        players += f", {match.bots} bots"
    return Activity(f"{mode_label} on {map_label}", players, ICON_KEY, ICON_TEXT, started_at)


def client_pid() -> int | None:
    # tasklist is available on the supported Windows client and needs no extra package.
    # Decode the bytes ourselves against the ANSI code page: tasklist emits
    # console-encoded text (CP936 on a zh-CN box), so letting Python decode it
    # via text=True throws UnicodeDecodeError whenever UTF-8 mode is forced
    # (PYTHONUTF8=1 / PYTHONIOENCODING=utf-8), which used to take the whole
    # helper down with an AttributeError on the resulting None stdout.
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq C1.exe", "/FO", "CSV", "/NH"],
        capture_output=True, timeout=5, check=False,
        # 本进程由栈以 pythonw 无控制台方式拉起；这里若不给 CREATE_NO_WINDOW，
        # Windows 会给 tasklist 单独分配一个控制台，而默认控制台宿主是 Windows
        # Terminal —— 于是每隔几秒就弹出一个终端窗口。必须显式隐藏。
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    raw = result.stdout or b""
    try:
        text = raw.decode("mbcs", errors="replace")
    except LookupError:            # not Windows: no ANSI code page
        text = raw.decode("utf-8", errors="replace")
    for row in csv.reader(text.splitlines()):
        if len(row) > 1 and row[0].lower() == "c1.exe" and row[1].isdigit():
            return int(row[1])
    return None


def process_started_at(pid: int) -> float:
    """Windows process creation time, used to reject a previous C1 log."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (ctypes.c_uint, ctypes.c_int, ctypes.c_uint)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetProcessTimes.argtypes = (ctypes.c_void_p,) + (ctypes.POINTER(ctypes.c_ulonglong),) * 4
    kernel.GetProcessTimes.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    handle = kernel.OpenProcess(0x1000, 0, pid)
    if not handle:
        return 0.0
    try:
        created = ctypes.c_ulonglong()
        exited = ctypes.c_ulonglong()
        kernel_time = ctypes.c_ulonglong()
        user_time = ctypes.c_ulonglong()
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                      ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return 0.0
        return created.value / 10_000_000 - 11_644_473_600
    finally:
        kernel.CloseHandle(handle)


def server_status(port: int, password: str) -> Match | None:
    packet = b"\xff" * 4 + b'rcon "' + password.encode("ascii") + b'" sh1x_status'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.7)
        try:
            sock.sendto(packet, ("127.0.0.1", port))
            return parse_status(sock.recv(8192).decode("ascii", errors="replace"))
        except (OSError, UnicodeError):
            return None


def pipe_bytes_available(pipe) -> int:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.PeekNamedPipe.argtypes = (
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint), ctypes.c_void_p)
    kernel.PeekNamedPipe.restype = ctypes.c_int
    available = ctypes.c_uint()
    handle = msvcrt.get_osfhandle(pipe.fileno())
    if not kernel.PeekNamedPipe(handle, None, 0, None, ctypes.byref(available), None):
        raise OSError("Discord RPC pipe closed")
    return available.value


def read_frame(pipe, timeout: float = 3.0) -> tuple[int, dict]:
    deadline = time.monotonic() + timeout
    while pipe_bytes_available(pipe) < 8:
        if time.monotonic() >= deadline:
            raise TimeoutError("Discord RPC handshake timed out")
        time.sleep(0.05)
    header = read_exact(pipe, 8)
    if len(header) != 8:
        raise OSError("Discord RPC pipe closed")
    opcode, length = struct.unpack("<II", header)
    if length > MAX_RPC_FRAME:
        raise OSError("Discord RPC frame too large")
    while pipe_bytes_available(pipe) < length:
        if time.monotonic() >= deadline:
            raise TimeoutError("Discord RPC handshake timed out")
        time.sleep(0.05)
    body = read_exact(pipe, length)
    if len(body) != length:
        raise OSError("Discord RPC frame truncated")
    return opcode, json.loads(body)


def read_exact(pipe, length: int) -> bytes:
    chunks = []
    remaining = length
    while remaining:
        chunk = pipe.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class DiscordRpc:
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.pipe = None
        self.connected = False
        self.pending = bytearray()

    def connect(self) -> bool:
        if os.name != "nt":
            return False
        for index in range(10):
            try:
                self.pipe = open(r"\\.\pipe\discord-ipc-" + str(index), "r+b", buffering=0)
                self._write(0, {"v": 1, "client_id": self.app_id})
                opcode, message = read_frame(self.pipe)
                if opcode != 1 or message.get("evt") != "READY":
                    raise OSError("Discord rejected RPC handshake")
                self.connected = True
                print("[discord] connected", flush=True)
                return True
            except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
                self.close()
        return False

    def _write(self, opcode: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if len(body) > MAX_RPC_FRAME:
            raise ValueError("Discord RPC payload too large")
        self.pipe.write(struct.pack("<II", opcode, len(body)) + body)
        self.pipe.flush()

    def pump(self) -> None:
        """Drain RPC replies and PING without a blocked reader holding the pipe."""
        if not self.connected:
            return
        while True:
            try:
                available = pipe_bytes_available(self.pipe)
            except OSError:
                self.connected = False
                return
            if available == 0:
                return
            self.pending.extend(self.pipe.read(min(available, MAX_RPC_FRAME + 8)))
            while len(self.pending) >= 8:
                opcode, length = struct.unpack_from("<II", self.pending)
                if length > MAX_RPC_FRAME:
                    raise OSError("Discord RPC frame too large")
                if len(self.pending) < length + 8:
                    break
                body = bytes(self.pending[8:8 + length])
                del self.pending[:8 + length]
                message = json.loads(body)
                if opcode == 2:
                    self.connected = False
                    return
                if opcode == 3:
                    self._write(4, message)
                if opcode == 1 and message.get("evt") == "ERROR":
                    data = message.get("data")
                    reason = data.get("message", "unknown reason") if isinstance(data, dict) else "unknown reason"
                    print(f"[discord] activity rejected by Discord: {reason}", file=sys.stderr, flush=True)
                elif opcode == 1 and message.get("cmd") == "SET_ACTIVITY":
                    print("[discord] activity accepted", flush=True)

    def set_activity(self, pid: int, activity: Activity | None) -> None:
        if not self.connected:
            return
        data = None if activity is None else {
            "type": 0,
            "details": activity.details,
            "state": activity.state,
            "timestamps": {"start": activity.started_at},
            "assets": {"large_image": activity.image, "large_text": activity.image_text},
        }
        self._write(1, {"cmd": "SET_ACTIVITY", "nonce": uuid.uuid4().hex,
                        "args": {"pid": pid, "activity": data}})

    def close(self) -> None:
        self.connected = False
        if self.pipe is not None:
            try:
                self.pipe.close()
            except OSError:
                pass
            self.pipe = None
        self.pending.clear()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-id", default=os.getenv("CODOL_DISCORD_APP_ID", DEFAULT_APPLICATION_ID))
    parser.add_argument("--log", type=Path, default=Path(r"E:\codol-classic\main\console_mp.log"))
    parser.add_argument("--rcon-file", type=Path,
                        default=Path(os.getenv("TEMP", ".")) / "codol-11113-e2e-20260928"
                        / "lobby" / "native_server_rcon.txt")
    parser.add_argument("--port", type=int, default=17733)
    parser.add_argument("--once", action="store_true", help="print verified state without connecting to Discord")
    args = parser.parse_args()
    if not args.once and (not args.app_id or not args.app_id.isdecimal()):
        parser.error("set CODOL_DISCORD_APP_ID to a CoDOL Discord application ID")
    try:
        password = args.rcon_file.read_text(encoding="ascii").strip()
        if not password or '"' in password:
            raise ValueError("invalid RCON credential")
    except (OSError, ValueError) as error:
        parser.error(f"cannot read local RCON credential: {error}")
    log = ClientLog(args.log)
    rpc = DiscordRpc(args.app_id or "")
    current_pid = None
    current_activity = None
    current_started_at = 0.0
    published_pid = None
    needs_send = True
    started_at = int(time.time())
    while True:
        try:
            pid = client_pid()
            if pid != current_pid:
                log.reset()
                started_at = int(time.time())
                current_started_at = process_started_at(pid) if pid else 0.0
            current_pid = pid
            if pid and args.log.exists() and args.log.stat().st_mtime >= current_started_at - 2:
                log.update()
            server = server_status(args.port, password) if pid and log.active else None
            match = verified_match(log, server)
            activity = activity_for(match, log.active_since if match else started_at) if pid else None
            if args.once:
                print(json.dumps({"client_running": bool(pid), "client_active": log.active if pid else False,
                                  "map": match.map_name if match else None,
                                  "gametype": match.mode if match else None,
                                  "presence": None if activity is None else {
                                      "details": activity.details, "state": activity.state,
                                      "large_image": activity.image}}, indent=2))
                return 0
            if not rpc.connected:
                rpc.close()
                if not rpc.connect():
                    time.sleep(5)
                    continue
                needs_send = True
            if needs_send or activity != current_activity:
                rpc.set_activity(pid or published_pid or os.getpid(), activity)
                current_activity = activity
                published_pid = pid if activity else None
                needs_send = False
                if activity:
                    print(f"[discord] {activity.details} | {activity.state}", flush=True)
                else:
                    print("[discord] cleared", flush=True)
            rpc.pump()
            time.sleep(3)
        except KeyboardInterrupt:
            try:
                if rpc.connected:
                    rpc.set_activity(current_pid or published_pid or os.getpid(), None)
            finally:
                rpc.close()
            return 0
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print(f"[discord] retrying after: {error}", file=sys.stderr, flush=True)
            rpc.close()
            current_activity = None
            needs_send = True
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
