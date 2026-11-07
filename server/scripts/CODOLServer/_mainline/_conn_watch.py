"""Watch every TCP endpoint a game process talks to.

Polls `netstat -ano` and records, for the given PID, every remote endpoint it
connects to (SYN_SENT / ESTABLISHED / TIME_WAIT).  This answers "is the client
also talking to some endpoint we are not listening on?" without touching the
game or the network stack.

ASCII only.  Usage: python -X utf8 _conn_watch.py <pid> <seconds> <out.jsonl>
"""
import json
import subprocess
import sys
import time

pid = int(sys.argv[1])
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
out = sys.argv[3] if len(sys.argv) > 3 else "conn_watch.jsonl"

t0 = time.time()
seen = {}
with open(out, "w", encoding="utf-8") as f:
    while time.time() - t0 < secs:
        try:
            txt = subprocess.run(["netstat", "-ano"], capture_output=True,
                                 text=True, timeout=10).stdout
        except Exception:
            time.sleep(0.5)
            continue
        for line in txt.splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[0] != "TCP":
                continue
            if parts[-1] != str(pid):
                continue
            local, remote, state = parts[1], parts[2], parts[3]
            key = (local, remote, state)
            if key in seen:
                continue
            seen[key] = True
            rec = {"t": round(time.time() - t0, 2), "local": local,
                   "remote": remote, "state": state}
            print(json.dumps(rec), flush=True)
            f.write(json.dumps(rec) + "\n")
        time.sleep(0.4)
