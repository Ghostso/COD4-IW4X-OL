"""One unattended attempt: ensure services, run the game, read the verdict.

Success  = uA50 reaches >= 3 (DW_LOBBY_CONNECTED) with no ERROR state name
Failure  = uA50 falls back to 0 while nm contains ERROR  (== the popup)

ASCII only.
Usage: python -X utf8 _auto_attempt.py --tag <name> [--seconds 60]
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LOBBY = os.path.join(ROOT, "CODOLServer", "lobby_server")
LOGS = os.path.join(ROOT, "CODOLServer", "logs")
AGENT = os.path.join(HERE, "agent_client.py")
WATCH = os.path.join(HERE, "_lobby_watch.py")
GAMEDIR = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923")


def sh(args, **kw):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, **kw)


def port_up(port):
    out = sh(["netstat", "-ano"]).stdout
    for line in out.splitlines():
        if (":%d" % port) in line and "LISTENING" in line:
            return True
    return False


def start_services(log):
    started = []
    jobs = [
        (8443, [sys.executable, "-X", "utf8",
                os.path.join(LOBBY, "lobby_probe_server.py"),
                "--cert-dir", LOBBY, "--bind", "127.0.0.1", "--port", "8443",
                "--log", os.path.join(LOGS, "lobby_probe.jsonl")]),
        (8444, [sys.executable, "-X", "utf8",
                os.path.join(LOBBY, "lobby_socket_server.py"),
                "--cert-dir", LOBBY, "--bind", "127.0.0.2", "--port", "8444",
                "--log", os.path.join(LOGS, "lobby_socket.jsonl")]),
    ]
    for port, argv in jobs:
        if port_up(port):
            log("service %d already listening" % port)
            continue
        p = subprocess.Popen(argv, cwd=ROOT,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             creationflags=0x00000008)  # DETACHED_PROCESS
        started.append((port, p.pid))
        log("started service %d pid=%d" % (port, p.pid))
    time.sleep(2.5)
    return started


def read_verdict(outdir):
    path = os.path.join(outdir, "watch.jsonl")
    if not os.path.exists(path):
        return {"verdict": "NO_LOG"}
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if "ev" in o:
            continue
        rows.append(o)
    if not rows:
        return {"verdict": "NO_SAMPLES"}
    reached = set()
    last = None
    saw_err = False
    for r in rows:
        u = r.get("uA50")
        if u is not None:
            reached.add(u)
        nm = r.get("nm") or ""
        if "ERROR" in nm:
            saw_err = True
        last = r
    ok = any(isinstance(u, int) and u >= 3 for u in reached) and not saw_err
    return {
        "verdict": "SUCCESS" if ok else "FAIL",
        "uA50_states": sorted(u for u in reached if u is not None),
        "sub_states": sorted({r.get("sub_state") for r in rows
                              if r.get("sub_state") is not None}),
        "last_nm": last.get("nm"),
        "last_err": last.get("last_err"),
        "last_obj_code": last.get("obj_code"),
        "saw_error_name": saw_err,
        "samples": len(rows),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--seconds", type=float, default=60.0)
    a = ap.parse_args()

    def log(msg):
        print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)

    log("dwauth.ini = %r" % open(os.path.join(GAMEDIR, "dwauth.ini"),
                                 encoding="ascii").read())
    start_services(log)

    outdir = os.path.join(HERE, "_auto_" + a.tag)
    os.makedirs(outdir, exist_ok=True)
    log("running game (%.0fs) -> %s" % (a.seconds, outdir))
    r = sh([sys.executable, "-X", "utf8", AGENT, "run",
            sys.executable, "-X", "utf8", WATCH,
            "--cwd", GAMEDIR, "--out", outdir,
            "--seconds", str(a.seconds), "--step", "0.5"],
           timeout=a.seconds + 180)
    log("watcher rc=%d" % r.returncode)
    v = read_verdict(outdir)
    print(json.dumps(v, ensure_ascii=False, indent=2))
    return 0 if v.get("verdict") == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
