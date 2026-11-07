"""Sweep candidate reply bodies for the client's `GET /` request.

For each variant: write lobby_server/probe_response.txt, restart the probe on
8443, run one game, then report the BD fields we care about:

    http_464   the status code the client stored (want 200)
    http_444   the BD state (5 == BD_DONE is the goal)
    uA50       lobby state (3 == DW_LOBBY_CONNECTED is success)
    sub_state  (9 == auth finished)

Never runs two services and never touches the elevated agent.
ASCII only.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LOBBY = os.path.join(ROOT, "CODOLServer", "lobby_server")
AGENT = os.path.join(HERE, "agent_client.py")
BDW = os.path.join(HERE, "_bdfield_watch.py")
GAMEDIR = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923")
PROBE_FILE = os.path.join(LOBBY, "probe_response.txt")
AGENT_PID = 17900

VARIANTS = [
    ("v1_empty", "status=200\n"),
    ("v2_brace", "status=200\nbody={}\n"),
    ("v3_code700", 'status=200\nbody={"code":700}\n'),
    ("v4_404", "status=404\n"),
    ("v5_204", "status=204\n"),
]


def sh(args, timeout=300):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout)


def pids_on(port):
    out = sh(["netstat", "-ano"]).stdout
    res = set()
    for line in out.splitlines():
        if (":%d" % port) in line and "LISTENING" in line:
            p = line.split()[-1]
            if p.isdigit():
                res.add(int(p))
    return res


def kill_probe():
    for p in pids_on(8443):
        if p == AGENT_PID:
            continue
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Stop-Process -Id %d -Force -ErrorAction SilentlyContinue"
                        % p], cwd=ROOT, capture_output=True)
    time.sleep(1.0)


def start_probe():
    subprocess.Popen(
        [sys.executable, "-X", "utf8",
         os.path.join(LOBBY, "lobby_probe_server.py"),
         "--cert-dir", LOBBY, "--bind", "127.0.0.1", "--port", "8443",
         "--log", os.path.join(ROOT, "CODOLServer", "logs",
                               "lobby_probe.jsonl")],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=0x00000008)
    time.sleep(2.0)


def game_alive():
    out = sh(["powershell", "-NoProfile", "-Command",
              "(Get-Process codoMP_client_shipRetail "
              "-ErrorAction SilentlyContinue | Measure-Object).Count"]).stdout
    return out.strip().isdigit() and int(out.strip()) > 0


def read_bd(outdir):
    path = os.path.join(outdir, "bd.jsonl")
    if not os.path.exists(path):
        return None
    best = None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if "ev" in o:
            continue
        if o.get("httpobj"):
            if best is None or o.get("t", 0) >= best.get("t", 0):
                best = o
    return best


def main():
    results = []
    for tag, body in VARIANTS:
        open(PROBE_FILE, "w", encoding="ascii", newline="").write(body)
        print("\n=== %s : %r ===" % (tag, body), flush=True)
        kill_probe()
        start_probe()
        outdir = os.path.join(HERE, "_sweep_" + tag)
        if os.path.isdir(outdir):
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Remove-Item -Recurse -Force '%s'" % outdir],
                           cwd=ROOT, capture_output=True)
        r = sh([sys.executable, "-X", "utf8", AGENT, "run",
                sys.executable, "-X", "utf8", BDW,
                "--cwd", GAMEDIR, "--out", outdir,
                "--seconds", "40", "--step", "0.5"], timeout=240)
        bd = read_bd(outdir)
        if not bd:
            print("  no BD sample captured", flush=True)
            results.append({"variant": tag, "verdict": "NO_SAMPLE"})
            continue
        row = {
            "variant": tag,
            "t": bd.get("t"),
            "uA50": bd.get("uA50"),
            "sub_state": bd.get("sub_state"),
            "last_err": bd.get("last_err"),
            "http_04": bd.get("http_04"),
            "http_444": bd.get("http_444"),
            "http_464": bd.get("http_464"),
        }
        results.append(row)
        print("  " + json.dumps(row), flush=True)
    print("\n===== SUMMARY =====")
    for r in results:
        print(json.dumps(r))
    json.dump(results, open(os.path.join(HERE, "_sweep_summary.json"), "w",
                            encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
