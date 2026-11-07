# -*- coding: utf-8 -*-
import os, subprocess, sys, time, json, socket, ssl

LS = os.path.join("CODOLServer","lobby_server")
PROBE = os.path.join(LS, "lobby_probe_server.py")
LOGD = os.path.join(LS, "logs3074b")
os.makedirs(LOGD, exist_ok=True)
logf = os.path.join(LOGD, "auth3074b.jsonl")
outf = open(os.path.join(LOGD,"auth3074b.out"), "wb")
errf = open(os.path.join(LOGD,"auth3074b.err"), "wb")

PY = sys.executable
argv = [PY,"-X","utf8","-u",PROBE,
        "--cert-dir", LS,
        "--bind","127.0.0.1","--port","3074",
        "--log", logf]
print("START:", " ".join(argv))
p = subprocess.Popen(argv, stdout=outf, stderr=errf, creationflags=0x08000000)
print("pid:", p.pid)
time.sleep(3.0)
print("alive:", p.poll() is None)
if p.poll() is not None:
    print("DIED rc=", p.returncode)
    print(open(os.path.join(LOGD,"auth3074b.err"),"rb").read().decode("utf-8","replace")[-1500:])
    sys.exit(1)
with open(logf,"rb") as f:
    print("LOG:", f.read().decode("utf-8","replace"))
