"""Drive the fixed launch chain until the client really reaches the lobby.

Each round:
  1. restart the probe server with the current lobby_response.json
  2. run the fixed launch chain through the elevated agent
  3. read the client's own DW state name plus the probe/socket logs
  4. decide whether the lobby was actually reached

Success requires BOTH the client state name and a real lobby socket event.
The observer may write explicitly requested diagnostic process fields; this
driver itself only restarts the local test server and inspects run artifacts.
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
    # lobby_socket_server.py has no --cert-dir argument (it binds a plain TCP
    # socket); passing it made argparse exit 2, so the 8444 listener never
    # came up and every round lost its lobby-channel socket log.
    q = subprocess.Popen([PY, "-X", "utf8", "-u", sock,
                          "--bind", "127.0.0.2", "--port", "8444",
                          "--log", os.path.join(log_dir, "socket.jsonl")],
                         stdout=sout, stderr=serr)
    time.sleep(3)
    return p, q


def launch(tag, seconds, poke_host="", poke_port=0, patch_lobby_result=-1,
           poke_lobby_globals=0, poke_lobby_5e8=0,
           poke_lobby_9c4=0,
           handshake_ready_file="", abort_on_cfg0=0,
           lobby_ready_only=0, handshake_echo_file="", post83_trace=0,
           post83_seconds=0,
           poke_lobby_644=0, handshake_key_file="", eip_trace=0,
           sandbox=""):
    script = os.path.join(ROOT, "run_codol_001", "capture_elevated_network.ps1")
    argv = [PY, "-X", "utf8", "agent_client.py", "run", "powershell",
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script,
            "-DurationSeconds", str(seconds)]
    if sandbox:
        argv += ["-Sandbox", sandbox]
    if poke_host:
        argv += ["-PokeLobbyHost", poke_host]
    if poke_port:
        argv += ["-PokeLobbyPort", str(poke_port)]
    if patch_lobby_result >= 0:
        argv += ["-PatchLobbyResult", str(patch_lobby_result)]
    if poke_lobby_globals:
        argv += ["-PokeLobbyGlobals", "1"]
    if poke_lobby_5e8:
        argv += ["-PokeLobby5e8", "1"]
    if poke_lobby_9c4:
        argv += ["-PokeLobby9c4", "1"]
    if handshake_ready_file:
        argv += ["-HandshakeReadyFile", handshake_ready_file]
    if abort_on_cfg0:
        argv += ["-AbortOnCfg0", "1"]
    if lobby_ready_only:
        argv += ["-LobbyReadyOnly", "1"]
    if handshake_echo_file:
        argv += ["-HandshakeEchoFile", handshake_echo_file]
    if post83_trace:
        argv += ["-Post83Trace", "1"]
    if post83_seconds:
        argv += ["-Post83Seconds", str(post83_seconds)]
    if poke_lobby_644:
        argv += ["-PokeLobby644", "1"]
    if handshake_key_file:
        argv += ["-HandshakeKeyFile", handshake_key_file]
    if eip_trace:
        argv += ["-EipTrace", "1"]
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
                    help="fill lobby host/port globals only; do not alter request state")
    ap.add_argument("--poke-lobby-5e8", action="store_true",
                    help="experimental: force [req+0x5E8] 1->2 once C8==2")
    ap.add_argument("--poke-lobby-9c4", action="store_true",
                    help="experimental: force [req+0x9C]=4 once C8==2")
    ap.add_argument("--handshake-ready-file", default="",
                    help="file written after [req+0x5E8] is forced to 2")
    ap.add_argument("--abort-on-cfg0", action="store_true",
                    help="terminate a round early when cfg_applied stays 0")
    ap.add_argument("--lobby-ready-only", action="store_true",
                    help="signal readiness without rewriting [req+0x5E8]")
    ap.add_argument("--handshake-echo-file", default="",
                    help="file where observer publishes live [req+0x5FC]")
    ap.add_argument("--post83-trace", action="store_true",
                    help="tight sampling of the reader after 5E8 reaches 3")
    ap.add_argument("--post83-seconds", type=int, default=0,
                    help="how long to keep sampling after 5E8 reaches 3 "
                         "(0 = observer default 70)")
    ap.add_argument("--poke-lobby-644", action="store_true",
                    help="experimental: force [req+0x644]=3 after 5E8 reaches 3")
    ap.add_argument("--handshake-key-file", default="",
                    help="file where observer publishes the 20-byte 0x620 source")
    ap.add_argument("--eip-trace", action="store_true",
                    help="sample thread EIPs inside 0xBA0000-0xBB0000")
    ap.add_argument("--sandbox", default="",
                    help="override the sandbox directory the observer launches "
                         "(default: the observer's built-in sandbox)")
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
                           int(a.poke_lobby_globals),
                           int(a.poke_lobby_5e8),
                           int(a.poke_lobby_9c4),
                           a.handshake_ready_file,
                           int(a.abort_on_cfg0),
                           int(a.lobby_ready_only),
                           a.handshake_echo_file,
                           int(a.post83_trace),
                           a.post83_seconds,
                           int(a.poke_lobby_644),
                           a.handshake_key_file,
                           int(a.eip_trace),
                           a.sandbox)
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
            stop_probe()
            return 0

    print("rounds exhausted without DW_LOBBY_CONNECTED", flush=True)
    # stop_probe() only runs at the *start* of a round; without this the
    # 8443/8444 listeners leak after the final attempt.
    stop_probe()
    return 1


if __name__ == "__main__":
    sys.exit(main())
