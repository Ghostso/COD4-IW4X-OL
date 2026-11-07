# -*- coding: utf-8 -*-
import os, subprocess, sys, time
LS = os.path.join("CODOLServer","lobby_server")
PLAIN = os.path.join(LS, "lobby_plain_probe.py")
LOGD = os.path.join(LS, "logs3074b")
os.makedirs(LOGD, exist_ok=True)
logf = os.path.join(LOGD,"lsg3074b.jsonl")
outf = open(os.path.join(LOGD,"lsg3074b.out"), "wb")
errf = open(os.path.join(LOGD,"lsg3074b.err"), "wb")
PY = sys.executable
argv = [PY,"-X","utf8","-u",PLAIN,
        "--bind","127.0.0.2","--port","3074",
        "--log", logf,
        "--lobby-handshake","--magic","0xDC",
        "--hold-after-83","120"]
print("START:", " ".join(argv))
p = subprocess.Popen(argv, stdout=outf, stderr=errf, creationflags=0x08000000)
print("pid:", p.pid)
time.sleep(3.0)
print("alive:", p.poll() is None)
with open(logf,"rb") as f: print("LOG:", f.read().decode("utf-8","replace"))
if p.poll() is not None:
    print("ERR:", open(os.path.join(LOGD,"lsg3074b.err"),"rb").read().decode("utf-8","replace")[-1200:])
