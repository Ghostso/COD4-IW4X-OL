# -*- coding: utf-8 -*-
"""Shared server side for the independent native battle chain.

Both public entry points use this file. It starts the native combat server,
the local TLS auth service, and the local Lobby service. It never starts the
game client; the frozen entry does that after this stack is ready.
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
COMBAT = CHAIN / "combat"
LOGS = CHAIN / "logs"
READY = CHAIN / "stack_ready.json"

def tcp_ready(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False

def udp_ready(port):
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "UDP"], capture_output=True, text=True, errors="replace", timeout=5).stdout
    except Exception:
        return False
    return any((":" + str(port)) in line for line in out.splitlines())

def wait_for(fn, timeout, label):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if fn():
            return True
        time.sleep(0.25)
    print("[native-chain] timeout waiting for " + label, flush=True)
    return False

def stop(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=600)
    args = ap.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)
    try:
        READY.unlink()
    except FileNotFoundError:
        pass
    key_path = KIT / "battle_security_key.txt"
    if not key_path.is_file() or len(key_path.read_text(encoding="ascii").strip()) != 32:
        raise SystemExit("missing or invalid native battle_security_key.txt")
    combat = auth = lobby = None
    handles = []
    try:
        combat_log = (LOGS / "combat_server.log").open("w", encoding="utf-8")
        combat = subprocess.Popen([str(COMBAT / "CODOLCombatServer.exe"), "--run", "--config", "config/firingrange_live.cfg", "--max-seconds", str(args.seconds)], cwd=str(COMBAT), stdout=combat_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        handles.append(combat_log)
        if not wait_for(lambda: udp_ready(28960), 15, "UDP 28960"):
            raise SystemExit("native combat server did not bind UDP 28960")
        auth_log = (LOGS / "auth3074.log").open("w", encoding="utf-8")
        auth = subprocess.Popen([sys.executable, "-X", "utf8", str(KIT / "fake_auth_tls.py")], cwd=str(KIT), stdout=auth_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        handles.append(auth_log)
        if not wait_for(lambda: tcp_ready("127.0.0.1", 3074), 15, "TLS auth 127.0.0.1:3074"):
            raise SystemExit("auth service did not bind 127.0.0.1:3074")
        lobby_log = (LOGS / "lobby_server.log").open("w", encoding="utf-8")
        lobby = subprocess.Popen([sys.executable, "-X", "utf8", str(KIT / "lobby_server.py"), "--lobby-bind", "127.0.0.2", "--lobby-port", "3074"], cwd=str(KIT), stdout=lobby_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        handles.append(lobby_log)
        if not wait_for(lambda: tcp_ready("127.0.0.2", 3074), 15, "Lobby 127.0.0.2:3074"):
            raise SystemExit("Lobby service did not bind 127.0.0.2:3074")
        READY.write_text(json.dumps({"combat_pid": combat.pid, "auth_pid": auth.pid, "lobby_pid": lobby.pid, "client_started": False, "udp": "127.0.0.1:28960", "auth": "127.0.0.1:3074", "lobby": "127.0.0.2:3074"}, indent=2), encoding="utf-8")
        print("NATIVE_CHAIN_READY client_started=false", flush=True)
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            time.sleep(1)
    finally:
        for p in (lobby, auth, combat):
            stop(p)
        for h in handles:
            try:
                h.close()
            except Exception:
                pass
        try:
            READY.unlink()
        except FileNotFoundError:
            pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
