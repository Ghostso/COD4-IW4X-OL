# -*- coding: utf-8 -*-
"""Independent local engine chain.

It reuses the copied auth/Lobby/nt10 launcher, but explicitly disables the
standalone C battle server. After nt10 has created the client, the attach
stage enables the in-process Localnet32 engine path.
"""
from __future__ import annotations
import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

CHAIN = Path(__file__).resolve().parents[1]
KIT = CHAIN / "kit"
GAME = CHAIN / "game"
LOGS = CHAIN / "logs"
ATTACH = CHAIN / "scripts" / "native_engine_attach.py"
BOOTSTRAP = CHAIN / "scripts" / "native_engine_bootstrap.py"
TARGET = "codoMP_client_shipRetail.exe"


def client_pids():
    """Return current client PIDs without treating the on-disk EXE as a process."""
    r = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq " + TARGET, "/FO", "CSV", "/NH"],
        capture_output=True, text=True, errors="replace",
    )
    out = []
    for line in r.stdout.splitlines():
        cols = [x.strip('"') for x in line.split('","')]
        if cols and cols[0].casefold() == TARGET.casefold():
            try:
                out.append(int(cols[1].replace(",", "")))
            except (IndexError, ValueError):
                pass
    return out


def event(path, stage, **data):
    row = {"ts": time.time(), "stage": stage, **data}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("[local-chain] " + json.dumps(row, ensure_ascii=False), flush=True)


def listening(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def window_snapshot(pid):
    """Return visible top-level windows belonging to one client PID."""
    import ctypes
    import ctypes.wintypes as wt
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    rows = []
    cb_type = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        owner = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != pid:
            return True
        title = ctypes.create_unicode_buffer(512)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, len(title))
        user32.GetClassNameW(hwnd, cls, len(cls))
        if user32.IsWindowVisible(hwnd):
            rows.append({"hwnd": int(hwnd), "title": title.value, "class": cls.value})
        return True
    user32.EnumWindows(cb_type(cb), 0)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=180)
    ap.add_argument("--game-root", required=True)
    ap.add_argument("--dedicated-bootstrap", action="store_true",
                    help="显式使用 -q -qa 原生 Dedicated 取证路径；默认走可见大厅客户端")
    ap.add_argument("--keep-iips", action="store_true",
                    help="Dedicated 取证时保留 enable_iips=1（默认会改成 0）")
    a = ap.parse_args()
    game_root = Path(a.game_root).resolve()
    if not (game_root / "codoMP_client_shipRetail.exe").is_file():
        raise SystemExit("game root missing codoMP_client_shipRetail.exe: " + str(game_root))
    if not (game_root / "Ayria" / "Plugins" / "CodolGameServer.Localnet32").is_file():
        raise SystemExit("game root missing CodolGameServer.Localnet32: " + str(game_root))
    LOGS.mkdir(parents=True, exist_ok=True)
    launch_log = LOGS / "start_local_engine.jsonl"
    launch_log.write_text("", encoding="utf-8")
    before = client_pids()
    event(launch_log, "preflight", game_root=str(game_root), seconds=a.seconds,
          existing_client_pids=before)
    if before:
        event(launch_log, "refuse_existing_client", ok=False,
              reason="client already running", pids=before)
        return 3
    # Do not let a previous run's frame-hook line make this run look healthy.
    # The game writes these files in the selected sandbox before the attach
    # helper starts, so clear only the three local-engine diagnostics here.
    game_log_dir = game_root / "Ayria" / "Logs"
    for name in ("CodolGameServer.log", "Bootstrapper32.log", "Localnetworking.log"):
        path = game_log_dir / name
        if path.exists():
            try:
                path.write_text("", encoding="utf-8")
            except OSError as exc:
                event(launch_log, "clear_engine_log", ok=False,
                      log_path=str(path), error=repr(exc))
            else:
                event(launch_log, "clear_engine_log", ok=True, log_path=str(path))
    iips_ini = game_root / "iips.ini"
    iips_backup = game_root / "iips.ini.bak_before_local_chain_disable_20261019"
    if iips_ini.is_file() and not getattr(a, "keep_iips", False):
        original_iips = iips_ini.read_text(encoding="utf-8", errors="replace")
        if not iips_backup.exists():
            iips_backup.write_text(original_iips, encoding="utf-8")
        if "enable_iips=1" in original_iips:
            iips_ini.write_text(original_iips.replace("enable_iips=1", "enable_iips=0", 1), encoding="utf-8")
            event(launch_log, "iips_local_disable", ok=True, iips_path=str(iips_ini),
                  backup=str(iips_backup), before=original_iips.strip(),
                  after=iips_ini.read_text(encoding="utf-8").strip())
        else:
            event(launch_log, "iips_local_disable", ok=True, iips_path=str(iips_ini),
                  backup=str(iips_backup), before=original_iips.strip(),
                  after=original_iips.strip(), already_disabled=True)
    # Default mode reuses the verified Auth/Lobby/nt10 client path. The native
    # module is attached to that same visible client; no C battle server starts.
    if a.dedicated_bootstrap:
        cmd = [sys.executable, "-X", "utf8", str(KIT / "run_all.py"),
               "--secs", str(a.seconds), "--services-only",
               "--no-battle", "--game-root", a.game_root]
    else:
        cmd = [sys.executable, "-X", "utf8", str(KIT / "run_all.py"),
               "--secs", str(a.seconds), "--no-battle",
               "--nt10-delay", "2.5", "--game-root", a.game_root]
    env = os.environ.copy()
    env["CODOL_LOCAL_ENGINE_CHAIN"] = "1"
    if a.dedicated_bootstrap:
        # Dedicated-only environment. The visible lobby client must not inherit
        # this role or it will skip the normal Lobby/TCLS path.
        env["OLMOD_PROCESS_ROLE"] = "dedicated"
        env["OLMOD_DEDICATED_CONTROL_PORT"] = "28961"
        env["OLMOD_CLIENT_BRIDGE_PORT"] = "28962"
        env["OLMOD_CONSOLE_LOG"] = "1"
    else:
        # Combined role keeps the ordinary Lobby/TCLS path while allowing the
        # in-process native plugin to claim its local control channel later.
        env["OLMOD_PROCESS_ROLE"] = "combined"
        env["OLMOD_DEDICATED_CONTROL_PORT"] = "28961"
        env["OLMOD_CLIENT_BRIDGE_PORT"] = "28962"
        env["OLMOD_CONSOLE_LOG"] = "1"
        env["OLMOD_CLAIM_LOBBY"] = "1"
    launcher = subprocess.Popen(cmd, cwd=str(KIT), env=env)
    event(launch_log, "launcher_started", pid=launcher.pid, command=cmd)
    bootstrap = None
    try:
        deadline = time.monotonic() + 90
        if a.dedicated_bootstrap:
            while time.monotonic() < deadline:
                if listening("127.0.0.1", 3074) and listening("127.0.0.2", 3074):
                    event(launch_log, "services_ready", ok=True,
                          auth="127.0.0.1:3074", lobby="127.0.0.2:3074")
                    break
                if launcher.poll() is not None:
                    event(launch_log, "launcher_exit_before_client", ok=False,
                          returncode=launcher.returncode)
                    return launcher.returncode or 1
                time.sleep(0.5)
            else:
                event(launch_log, "services_timeout", ok=False)
                return 2
            native_cmd = [sys.executable, "-X", "utf8", str(BOOTSTRAP),
                          "--game-root", a.game_root,
                          "--seconds", str(a.seconds),
                          "--out", str(LOGS / "native_engine_bootstrap.txt")]
            bootstrap = subprocess.Popen(native_cmd, cwd=str(CHAIN), env=env)
            event(launch_log, "native_bootstrap_started", pid=bootstrap.pid,
                  command=native_cmd, mode="dedicated")
            rc = bootstrap.wait()
            event(launch_log, "native_bootstrap_exit", ok=(rc == 0), returncode=rc)
            return rc

        # Visible mode: nt10 owns client creation and retries. Do not attach to
        # the first PID: the known startup flake exits around four seconds and
        # nt10 immediately creates a replacement. Wait for a candidate to stay
        # alive before attaching, and record every candidate that disappears.
        pid = None
        first_seen = {}
        stable_for = 4.5
        while time.monotonic() < deadline:
            candidates = [p for p in client_pids() if p not in before]
            now = time.monotonic()
            for candidate in candidates:
                first_seen.setdefault(candidate, now)
                if now - first_seen[candidate] >= stable_for:
                    pid = candidate
                    break
            if pid:
                event(launch_log, "visible_client_stable", ok=True, pid=pid,
                      stable_seconds=round(now - first_seen[pid], 2),
                      windows=window_snapshot(pid), candidates=candidates)
                break
            for candidate in list(first_seen):
                if candidate not in candidates:
                    event(launch_log, "visible_client_candidate_exit", ok=False,
                          pid=candidate,
                          stable_seconds=round(now - first_seen[candidate], 2))
                    del first_seen[candidate]
            if launcher.poll() is not None:
                event(launch_log, "launcher_exit_before_client", ok=False,
                      returncode=launcher.returncode, candidates=candidates)
                if not candidates:
                    return launcher.returncode or 1
            time.sleep(0.25)
        if not pid:
            event(launch_log, "visible_client_timeout", ok=False,
                  current_client_pids=client_pids())
            return 2
        attach_cmd = [sys.executable, "-X", "utf8", str(ATTACH),
                      "--seconds", str(a.seconds), "--game-root", a.game_root,
                      "--pid", str(pid),
                      "--visible-mode",
                      "--out", str(LOGS / "native_engine_attach.jsonl")]
        bootstrap = subprocess.Popen(attach_cmd, cwd=str(CHAIN), env=env)
        event(launch_log, "native_attach_started", pid=bootstrap.pid,
              target_pid=pid, command=attach_cmd, mode="visible")
        rc = bootstrap.wait()
        windows = window_snapshot(pid)
        ready_flag = KIT / "lobby_ready.flag"
        visible_ok = bool(windows) or ready_flag.exists()
        event(launch_log, "visible_client_acceptance", ok=(rc == 0 and visible_ok),
              returncode=rc, target_pid=pid, windows=windows,
              lobby_ready=ready_flag.exists())
        return rc if (rc != 0 or visible_ok) else 20
    finally:
        if bootstrap is not None and bootstrap.poll() is None:
            bootstrap.terminate()
        if launcher.poll() is None:
            launcher.terminate()
            try:
                launcher.wait(timeout=5)
            except Exception:
                launcher.kill()

if __name__ == "__main__":
    raise SystemExit(main())
