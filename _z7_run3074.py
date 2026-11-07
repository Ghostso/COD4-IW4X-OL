# -*- coding: utf-8 -*-
"""Launch the frozen chain against the 3074 lobby servers, then watch for the
"cannot connect to lobby service" popup.  Per the working doc the popup does
NOT auto-dismiss, so a live process is not evidence of success.

Writes:
  CODOLServer/lobby3074/logs/run_<ts>.log
"""
import json
import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SECRETS = r"D:\z7tmp\secrets.txt"
RUNS = os.path.join(ROOT, "run_codol_001", "runs")
SANDBOX = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923")
SHM = os.path.join(ROOT, "CODOLServer", "_subagents", "_tenproxy_shm_fixed.bin")


def agent_run(argv, timeout=400):
    st = json.load(open(os.path.join(ROOT, "CODOLServer", "logs",
                                     "elevated_agent.json"), encoding="utf-8"))
    req = {"action": "run", "argv": argv, "token": st["token"]}
    s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=timeout)
    s.sendall((json.dumps(req) + "\n").encode("utf-8"))
    buf = b""
    while not buf.endswith(b"\n"):
        c = s.recv(65536)
        if not c:
            break
        buf += c
    return json.loads(buf.decode("utf-8"))


def game_pids():
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process | Where-Object {$_.ProcessName -match "
         "'codoMP_client_shipRetail|AboProbe'} | "
         "ForEach-Object { '{0}|{1}' -f $_.Id,$_.ProcessName }"],
        capture_output=True)
    out = r.stdout.decode("utf-8", "replace").strip()
    res = []
    for line in out.splitlines():
        line = line.strip()
        if "|" in line:
            pid, name = line.split("|", 1)
            res.append((int(pid), name))
    return res


def find_popup():
    """Look for the #32770 popup / the lost-connection text in the newest run."""
    if not os.path.isdir(RUNS):
        return None
    cands = [d for d in os.listdir(RUNS) if d.startswith("IFS1_ELEVATED_")]
    if not cands:
        return None
    newest = max((os.path.join(RUNS, d) for d in cands), key=os.path.getmtime)
    f = os.path.join(newest, "aboprobe.stdout")
    if not os.path.isfile(f):
        return None
    try:
        txt = open(f, "rb").read().decode("gbk", "replace")
    except OSError:
        return None
    hits = []
    if "#32770" in txt:
        hits.append("#32770")
    for s in ["与大厅服务失去连接", "无法连接大厅服务", "警告码"]:
        if s in txt:
            hits.append(s)
    return (newest, hits)


def main():
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    os.makedirs(os.path.dirname(SECRETS), exist_ok=True)
    if os.path.exists(SECRETS):
        os.remove(SECRETS)

    argv = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            os.path.join("run_codol_001", "elevated_ifs1_observer.ps1"),
            "-DurationSeconds", str(dur),
            "-Sandbox", SANDBOX,
            "-TenProxyShm", SHM,
            "-SecretsFile", SECRETS,
            "-Compat4", "1",
            "-PatchDelay", "42",
            "-PokeLobbyHost", "127.0.0.1",
            "-PokeLobbyPort", "3074",
            "-PokeLobbyGlobals", "1",
            "-Post83Trace", "1", "-Post83Seconds", "90",
            "-LobbyReadyOnly", "1"]
    print("launching (duration %ds) ..." % dur, flush=True)
    print("  secrets -> %s" % SECRETS, flush=True)
    r = agent_run(argv, timeout=dur + 120)
    print("agent rc:", r.get("rc"), flush=True)
    if r.get("stderr"):
        print("stderr:", r["stderr"][:500], flush=True)
    print("stdout:", (r.get("stdout") or "")[:800], flush=True)


if __name__ == "__main__":
    main()
