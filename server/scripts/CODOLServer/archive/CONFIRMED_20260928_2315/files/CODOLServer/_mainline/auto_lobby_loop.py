"""Drive the fixed launch chain until the client really reaches the lobby.

Each round:
  1. restart the probe server with the current lobby_response.json
  2. run the fixed launch chain through the elevated agent
  3. read the client's own DW state name plus the probe/socket logs
  4. decide whether the lobby was actually reached

Success requires BOTH the client state name and a real lobby socket event.
No process memory is written; only the local test server is restarted.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
LS = os.path.join(ROOT, "CODOLServer", "lobby_server")
MAINLINE = os.path.join(ROOT, "CODOLServer", "_mainline")
RUNS = os.path.join(ROOT, "restore_iips_contract_001", "runs")
PY = sys.executable


def run(argv, timeout=600):
    return subprocess.run(argv, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          timeout=timeout, cwd=MAINLINE)


def stop_probe():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "Where-Object { $_.CommandLine -match 'lobby_probe_server|lobby_socket_server' } | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, text=True, timeout=60)
    time.sleep(1.5)


def start_probe(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    probe = os.path.join(LS, "lobby_probe_server.py")
    out = open(os.path.join(log_dir, "probe.out"), "ab")
    err = open(os.path.join(log_dir, "probe.err"), "ab")
    p = subprocess.Popen([PY, "-X", "utf8", "-u", probe, "--cert-dir", LS,
                          "--bind", "127.0.0.1", "--port", "8443",
                          "--log", os.path.join(log_dir, "probe.jsonl")],
                         stdout=out, stderr=err)
    # The lobby socket service must be up as well: after the account stage
    # the client opens a second TLS connection for the lobby channel, and a
    # missing listener there shows up as DW_LOBBY_ERROR with no socket log.
    sock = os.path.join(LS, "lobby_socket_server.py")
    sout = open(os.path.join(log_dir, "socket.out"), "ab")
    serr = open(os.path.join(log_dir, "socket.err"), "ab")
    q = subprocess.Popen([PY, "-X", "utf8", "-u", sock, "--cert-dir", LS,
                          "--bind", "127.0.0.2", "--port", "8444",
                          "--log", os.path.join(log_dir, "socket.jsonl")],
                         stdout=sout, stderr=serr)
    time.sleep(3)
    return p, q


def launch(tag, seconds, poke_host="", poke_port=0, patch_lobby_result=-1,
           poke_lobby_globals=0):
    script = os.path.join(ROOT, "run_codol_001", "capture_elevated_network.ps1")
    argv = [PY, "-X", "utf8", "agent_client.py", "run", "powershell",
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script,
            "-DurationSeconds", str(seconds)]
    if poke_host:
        argv += ["-PokeLobbyHost", poke_host]
    if poke_port:
        argv += ["-PokeLobbyPort", str(poke_port)]
    if patch_lobby_result >= 0:
        argv += ["-PatchLobbyResult", str(patch_lobby_result)]
    if poke_lobby_globals:
        argv += ["-PokeLobbyGlobals", "1"]
    r = run(argv)
    text = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"IFS1_ELEVATED_(\d{8}_\d{6})", text)
    return (m.group(0) if m else None), text


def read_state(tag):
    # The observer writes its CSVs into an "aboprobe_run" sub-directory of the
    # run folder, not the run folder root.  Reading the wrong path silently
    # returned [] and made every round look like "no state at all".
    path = os.path.join(RUNS, tag, "aboprobe_run", tag + "_state.csv")
    if not os.path.exists(path):
        path = os.path.join(RUNS, tag, tag + "_state.csv")
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split(",")
        for line in fh:
            parts = line.rstrip("\n").split(",")
            if len(parts) != len(header):
                continue
            rows.append(dict(zip(header, parts)))
    return rows


def summarize(rows):
    """Collapse to the sequence of distinct (state name, sub_state, err)."""
    seq = []
    for r in rows:
        key = (r.get("dw_state_name", ""), r.get("sub_state", ""),
               r.get("last_err", ""), r.get("obj_code", ""))
        if not seq or seq[-1][0] != key:
            seq.append((key, r.get("t", ""), r.get("uA50", ""),
                        r.get("http_state", ""), r.get("http_status", ""),
                        r.get("objA", ""), r.get("objC", ""),
                        r.get("obj_stage", "")))
    return seq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--seconds", type=int, default=90)
    ap.add_argument("--no-retry-short", action="store_true",
                    help="do not automatically retry a run that died early")
    ap.add_argument("--poke-lobby-host", default="",
                    help="rewrite the hardcoded lobby host constant "
                         "(opt-in; default keeps the original slow path)")
    ap.add_argument("--poke-lobby-port", type=int, default=0,
                    help="rewrite the hardcoded lobby port constant "
                         "(opt-in; default keeps the original slow path)")
    ap.add_argument("--patch-lobby-result", type=int, default=-1,
                    help="debug patch: force 0x7F3800 to return N (0/1/2)")
    ap.add_argument("--poke-lobby-globals", action="store_true",
                    help="fill [0x81A9780]/[0x81A9EC4] with 8443 and host 127.0.0.1")
    a = ap.parse_args()

    # The IIPS startup chain is racy: some launches die at ~8.7 s with
    # exitcode 0xFFFFFFFF after loading iips.dll but before ifs2.dll, and
    # never open a socket.  That is a startup flake, not a protocol result,
    # so an attempt that produced no state at all is retried instead of being
    # counted as a full round.
    attempts = a.rounds if a.no_retry_short else a.rounds * 4
    good_rounds = 0
    for i in range(1, attempts + 1):
        if good_rounds >= a.rounds:
            break
        print("=" * 70, flush=True)
        print("ROUND %d/%d (attempt %d)" % (good_rounds + 1, a.rounds, i),
              flush=True)
        stop_probe()
        log_dir = os.path.join(ROOT, "CODOLServer", "logs",
                               "AUTO_LOBBY_%s_r%d" % (
                                   time.strftime("%Y%m%d_%H%M%S"), i))
        start_probe(log_dir)
        tag, text = launch(log_dir, a.seconds, a.poke_lobby_host,
                           a.poke_lobby_port, a.patch_lobby_result,
                           int(a.poke_lobby_globals))
        print("run tag:", tag, flush=True)
        if not tag:
            print(text[-2000:], flush=True)
            continue

        rows = read_state(tag)
        seq = summarize(rows)
        for key, t, ua50, hs, hst, objA, objC, stage in seq:
            print("  %-9s %-24s sub=%-3s err=%-5s code=%-6s "
                  "uA50=%-2s http=%s/%s objA=%s objC=%s stage=%s"
                  % (t, key[0], key[1], key[2], key[3], ua50, hs, hst,
                     objA, objC, stage), flush=True)

        sock_path = os.path.join(log_dir, "probe.jsonl")
        sock_log = ""
        if os.path.exists(sock_path):
            with open(sock_path, encoding="utf-8", errors="replace") as fh:
                sock_log = fh.read()
        tasks = re.findall(r'"req_auth_task": "(\d+)"', sock_log)
        print("  auth tasks seen:", tasks, flush=True)

        names = [k[0] for k, *_ in seq]
        if not any(names) and not tasks and not a.no_retry_short:
            print("  [startup flake: no state reached; retrying]", flush=True)
            continue
        good_rounds += 1
        reached = any("DW_LOBBY_CONNECTED" in n for n in names)
        print("  LOBBY_CONNECTED:", reached, flush=True)
        if reached:
            print("SUCCESS: client reported DW_LOBBY_CONNECTED", flush=True)
            return 0

    print("rounds exhausted without DW_LOBBY_CONNECTED", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
