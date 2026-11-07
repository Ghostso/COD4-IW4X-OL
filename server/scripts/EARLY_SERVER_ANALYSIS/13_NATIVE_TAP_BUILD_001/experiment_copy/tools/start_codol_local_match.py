"""Start one native match server in an existing local C1/lobby test stack.

This leaves the client, lobby, and launcher backend alone. It refuses to start
when the match port is occupied; stop the existing match server first.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time


# Distinct MP rulesets with shipped playlist rows, installed maps, and bot
# waypoint graphs. Arena has no shipped rotation row and its live objective
# was not visible, so it is excluded.
# Gun Game has neither a playlist entry nor a rules script in this build.
LOCAL_MATCH_ROTATION = (
    ("mp_rust", "dom", "dom"),
    ("mp_nuked", "tdm", "war"),
    ("mp_killhouse_sh", "ffa", "dm"),
    ("mp_nuked", "kc", "conf"),
    ("mp_storm_spring", "hq", "koth"),
    ("mp_bog_sh", "sab", "sab"),
    ("mp_afghan", "sd", "sd"),
    ("mp_nuked", "dd", "dd"),
    ("mp_nuked", "ctf", "ctf"),
    ("mp_killhouse_sh", "inf", "infect"),
)
PLAYLIST_GAMETYPE = {native: playlist for _map, playlist, native in LOCAL_MATCH_ROTATION}
PLAYLIST_GAMETYPE["combat"] = "tdm"


def auto_player_target(map_name: str, gametype: str) -> int:
    """Small-map training targets, including the human players."""
    if gametype == "zm":
        return 0
    # Rust is present in the shipped Domination playlist, whose maximum is 12.
    if gametype == "dom" and map_name == "mp_rust":
        return 12
    map_target = 8 if map_name in ("mp_rust", "mp_killhouse_sh", "mp_bog_sh") else 12
    if gametype == "dm":
        return min(map_target, 6)
    return map_target


def next_local_match(state_file: Path) -> tuple[str, str, str]:
    try:
        previous = json.loads(state_file.read_text(encoding="ascii"))
    except (OSError, ValueError, TypeError):
        previous = {}
    pair = (previous.get("last_map"), previous.get("last_gametype"))
    for i, row in enumerate(LOCAL_MATCH_ROTATION):
        if (row[0], row[2]) == pair:
            return LOCAL_MATCH_ROTATION[(i + 1) % len(LOCAL_MATCH_ROTATION)]
    return LOCAL_MATCH_ROTATION[0]


def record_local_match(state_file: Path, map_name: str, gametype: str) -> None:
    staged = state_file.with_suffix(".tmp")
    staged.write_text(json.dumps({"last_map": map_name,
                                  "last_gametype": gametype}) + "\n", encoding="ascii")
    os.replace(staged, state_file)


def ensure_local_bootcamp_rotation(playlist_file: Path, map_name: str, gametype: str) -> None:
    """Give Boot Camp a repeatable local map *and mode* rotation."""
    raw = playlist_file.read_bytes()
    text = raw.decode("latin1")
    block = re.search(r"(?ms)^playlist 1\b.*?(?=^playlist 2\b)", text)
    if not block or "mp_killhouse_sh," not in block.group():
        raise RuntimeError("local Boot Camp playlist layout changed")
    desired = [f"{name},{playlist_gt},1" for name, playlist_gt, _native_gt in LOCAL_MATCH_ROTATION]
    existing = re.findall(r"(?m)^mp_[a-z0-9_]+,[a-z0-9_]+,1\s*$", block.group())
    if existing == desired:
        return
    backup = playlist_file.with_name(playlist_file.name + ".before-local-rotation")
    if not backup.exists():
        shutil.copy2(playlist_file, backup)
    revised = re.sub(r"(?m)^mp_[a-z0-9_]+,[a-z0-9_]+,1\r?\n?", "", block.group())
    revised += "\n".join(desired) + "\n"
    staged = playlist_file.with_name(playlist_file.name + ".tmp")
    staged.write_bytes((text[:block.start()] + revised + text[block.end():]).encode("latin1"))
    os.replace(staged, playlist_file)


def sync_lobby_rotation(state_file: Path, map_name: str, gametype: str) -> None:
    """Make the next Boot Camp Ready request match the just-started map."""
    try:
        state = json.loads(state_file.read_text(encoding="ascii"))
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError, TypeError):
        state = {}
    pair = (map_name, PLAYLIST_GAMETYPE.get(gametype, gametype))
    index = next((i for i, row in enumerate(LOCAL_MATCH_ROTATION)
                  if row[:2] == pair), 0)
    state["1"] = {"index": index, "map": map_name,
                  "source": "local-match-start"}
    staged = state_file.with_name(state_file.name + ".tmp")
    staged.write_text(json.dumps(state, indent=1) + "\n", encoding="ascii")
    os.replace(staged, state_file)


def sync_lobby_match_mode(resource_dir: Path, map_name: str, gametype: str) -> None:
    """Seed the first match, then let each Ready press select the next pair."""
    target = resource_dir / "local_match_mode.json"
    staged = target.with_suffix(".tmp")
    staged.write_text(json.dumps({"map": map_name, "gametype": gametype,
                                  "rotation_enabled": True}) + "\n",
                      encoding="ascii")
    os.replace(staged, target)


def refuse_another_server():
    result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                            text=True, check=True)
    names = {line.split(",", 1)[0].strip('"').lower() for line in result.stdout.splitlines()}
    if any(name.startswith("codol_dedrun") for name in names):
        raise RuntimeError("another native dedicated-server process is running; inspect and stop it first")


def rcon(port, password, command):
    packet = b"\xff" * 4 + b'rcon "' + password.encode("ascii") + b'" ' + command.encode("ascii")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.8)
        sock.sendto(packet, ("127.0.0.1", port))
        try:
            return sock.recv(8192).decode("ascii", errors="replace")
        except (socket.timeout, ConnectionResetError):
            return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--install", type=Path, required=True)
    ap.add_argument("--stack", type=Path, required=True)
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument("--map", help="pin a map; otherwise advance the local map rotation")
    ap.add_argument("--gametype")
    ap.add_argument("--difficulty", choices=("recruit", "regular", "hardened", "veteran"), default="recruit")
    ap.add_argument("--xp-scale", type=int, choices=range(5),
                    help="optional rank XP multiplier for this local match")
    ap.add_argument("--bots", default="auto", help="fixed bot count or auto player target by map and mode")
    ap.add_argument("--port", type=int, default=17733)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    install, stack, exe = args.install.resolve(), args.stack.resolve(), args.exe.resolve()
    state = stack / "lobby"
    home = stack / "server-home"
    rotation_state = stack / "local-match-map-rotation.json"
    scripts = root / "bin" / "home" / "codol_rawfiles"
    pid_file = stack / "local-stack-pids.json"
    for required in (install / "main", stack / "C1.exe", state / "securitykey.bin",
                     state / "native_server_rcon.txt", state / "resources", exe, scripts, pid_file):
        if not required.exists():
            ap.error(f"required local stack input missing: {required}")
    refuse_another_server()
    if args.map is None:
        args.map, _playlist_gt, args.gametype = next_local_match(rotation_state)
    elif args.gametype is None:
        args.gametype = "combat"
    if args.bots == "auto":
        player_target = auto_player_target(args.map, args.gametype)
        fixed_bots = 0
        bot_fill = player_target
        bot_max = max(0, player_target - 1)
    else:
        try:
            fixed_bots = int(args.bots)
        except ValueError:
            ap.error("bots must be auto or an integer from 0 to 16")
        if not 0 <= fixed_bots <= 16:
            ap.error("bots must be auto or an integer from 0 to 16")
        player_target = 0
        bot_fill = 0
        bot_max = 0
    if any(row[0] == args.map for row in LOCAL_MATCH_ROTATION):
        ensure_local_bootcamp_rotation(state / "resources" / "mp_playlists_shipRetail_cb2.info",
                                       args.map, args.gametype)
    # The UDP bind is the authoritative duplicate-server guard. A stale PID
    # record alone must not block recovery after a server has exited.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as guard:
        try:
            guard.bind(("0.0.0.0", args.port))
        except OSError:
            ap.error(f"UDP/{args.port} is already occupied; inspect its owner before starting another server")
    password = (state / "native_server_rcon.txt").read_text(encoding="ascii").strip()
    if not password or '"' in password:
        ap.error("invalid local RCON credential file")
    (home / "main").mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(root / "tools"))
    import codol_package
    codol_package.build_pack(str(home / "main" / codol_package.PACK))
    logs = stack / "local-stack-logs"
    logs.mkdir(exist_ok=True)
    command = [str(exe), "+set", "dedicated", "2", "+set", "fs_basepath", str(install),
               "+set", "fs_homepath", str(home), "+set", "codol_clientExe", str(stack / "C1.exe"),
               "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(args.port),
               "+set", "rcon_password", password, "+set", "logfile", "2", "+set", "logrcon", "1",
               "+set", "developer", "1", "+set", "codol_scriptPath", str(scripts),
               "+set", "codol_scriptOverlay", str(scripts), "+set", "codol_scriptNativeOverlay", str(scripts),
               "+set", "codol_securityKeyPath", str(state / "securitykey.bin"),
               "+set", "codol_admissionRequired", "0", "+set", "codol_profilePath", str(state / "resources"),
               "+set", "codol_zoneType", "mp", "+set", "codol_sessionMap", args.map,
               "+set", "g_gametype", args.gametype, "+set", "scr_codol_bots", str(fixed_bots),
               "+set", "scr_codol_botfill", str(bot_fill), "+set", "scr_codol_botmax", str(bot_max),
               "+set", "sv_botDifficulty", args.difficulty]
    if args.xp_scale is not None:
        command += ["+set", "scr_xpscale", str(args.xp_scale)]
    command += ["+map", args.map]
    with (logs / "server.stdout").open("ab") as out, (logs / "server.stderr").open("ab") as err:
        process = subprocess.Popen(command, cwd=exe.parent, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"native match server exited during startup ({process.returncode})")
            status = rcon(args.port, password, "sh1x_status")
            humans_match = re.search(r"\bhumans=(\d+)\b", status)
            bots_match = re.search(r"\bbots=(\d+)\b", status)
            humans = int(humans_match.group(1)) if humans_match else -1
            bots = int(bots_match.group(1)) if bots_match else -1
            expected_bots = (min(bot_max, max(0, player_target - humans))
                             if bot_fill and humans > 0 else fixed_bots)
            if f"map={args.map}" in status and f"gametype={args.gametype}" in status and bots == expected_bots:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("native match server did not reach the requested map, mode, and bot count")
        log = home / "main" / "qconsole.log"
        if bots > 0 and args.gametype != "zm" and "CoDOL bot difficulty: loaded recruit/regular/hardened/veteran" not in log.read_text(encoding="utf-8", errors="replace"):
            raise RuntimeError("exact-build bot difficulty table did not load")
        record = json.loads(pid_file.read_text(encoding="ascii"))
        record["server"] = process.pid
        pid_file.write_text(json.dumps(record, indent=2) + "\n", encoding="ascii")
        record_local_match(rotation_state, args.map, args.gametype)
        if any(row[0] == args.map for row in LOCAL_MATCH_ROTATION):
            sync_lobby_rotation(state / "resources" / "map_rotation.state.json", args.map, args.gametype)
            sync_lobby_match_mode(state / "resources", args.map, args.gametype)
        print(f"READY one native server PID {process.pid} udp/{args.port} {args.map}/{args.gametype} bots={bots} player_target={player_target or 'fixed'} difficulty={args.difficulty} xp_scale={args.xp_scale if args.xp_scale is not None else 'server default'}")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        raise


if __name__ == "__main__":
    main()
